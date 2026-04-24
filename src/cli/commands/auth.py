import getpass
from argparse import Namespace, ArgumentParser, Action, _SubParsersAction
from typing import Callable

from src.cli.utils import (
    CLIError,
    getUserIdFromLocalSession,
    printDictAsTableInCLI,
    printServiceResInCLI,
)
from src.services.user import getUserById, getUserIdByAccessToken, userLogin
from src.cli.session import clearLocalSession, saveLocalSession


def authParserBuilder(
    subparsers: _SubParsersAction,
    add_json: Callable[[ArgumentParser], Action],
) -> ArgumentParser:
    """
    构建 auth 子命令解析器
    """
    # auth
    auth_parser = subparsers.add_parser("auth", help="Authorization commands")
    auth_parser.usage = "immortality auth {login, logout} [-h]"
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command")

    # auth login
    login_parser = auth_subparsers.add_parser("login", help="User login")
    login_parser.usage = "immortality auth login [-h] [--json]"
    add_json(login_parser)
    login_parser.set_defaults(func=authLoginCMD)

    # auth logout
    logout_parser = auth_subparsers.add_parser("logout", help="User logout")
    logout_parser.usage = "immortality auth logout [-h] [--json]"
    add_json(logout_parser)
    logout_parser.set_defaults(func=authLogoutCMD)

    # auth whoami
    whoami_parser = auth_subparsers.add_parser("whoami", help="查看当前登录用户")
    whoami_parser.usage = "immortality auth whoami [-h] [--json]"
    add_json(whoami_parser)
    whoami_parser.set_defaults(func=authWhoamiCMD)


def authLoginCMD(args: Namespace) -> int:
    """
    用户登录
    """
    username = getattr(args, "username", None)
    if not isinstance(username, str) or username.strip() == "":
        username = input("Username / Email: ").strip()
    if username == "":
        raise CLIError("Username / Email cannot be empty", exit_code=2)

    password = getattr(args, "password", None)
    if not isinstance(password, str) or password.strip() == "":
        password = getpass.getpass("Password: ")
    if password == "":
        raise CLIError("Password cannot be empty", exit_code=2)

    res = userLogin(username=username, password=password)
    if res.get("status") != 200:
        clearLocalSession()
        printServiceResInCLI(res, as_json=args.json)
        return 1

    token = res.get("access_token")
    if not isinstance(token, str) or token.strip() == "":
        printServiceResInCLI(
            {"status": -1, "message": "Login success but token is missing"},
            as_json=args.json,
        )
        return 1

    user_id = getUserIdByAccessToken(token=token)
    saveLocalSession(
        {
            "access_token": token,
            "user_id": user_id,
        }
    )

    payload = {
        "status": 200,
        "message": f"Successfully logined as {username}",
        "user_id": user_id,
    }
    printServiceResInCLI(payload, as_json=args.json)
    return 0


def authLogoutCMD(args: Namespace) -> int:
    """
    用户退出登录
    """
    clearLocalSession()
    printServiceResInCLI(
        {"status": 200, "message": "Successfully logged out"},
        as_json=args.json,
    )
    return 0


def authWhoamiCMD(args: Namespace) -> int:
    """
    获取当前登录用户信息
    """
    user_id = getUserIdFromLocalSession()
    res = getUserById(id=user_id)
    user = res.get("user")

    if args.json:
        printServiceResInCLI(res, as_json=True)
    else:
        printDictAsTableInCLI(user)
    return 0 if res.get("status") == 200 else 1
