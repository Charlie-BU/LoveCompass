import getpass
from argparse import Namespace, ArgumentParser, Action, _SubParsersAction
from typing import Callable

from src.cli.utils import (
    CLIError,
    getUserIdFromLocalSession,
    printTableInCLI,
    printServiceResInCLI,
)
from src.services.user import getUserById, getUserIdByAccessToken, userLogin
from src.cli.session import clearLocalSession, saveLocalSession


def registerAuthSubparser(
    subparsers: _SubParsersAction,
    add_json: Callable[[ArgumentParser], Action],
) -> ArgumentParser:
    """
    注册 auth 子命令
    """
    # auth
    auth_parser = subparsers.add_parser("auth", help="Authorization commands")
    auth_parser.usage = "immortality auth {login, logout, whoami} [-h]"
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command")

    # auth login
    login_parser = auth_subparsers.add_parser("login", help="User login")
    login_parser.usage = "immortality auth login [--username <username> --password <password>] [-h] [--json]"
    add_json(login_parser)
    login_parser.add_argument("--username", required=False, help="Username or email")
    login_parser.add_argument("--password", required=False, help="Password")
    login_parser.set_defaults(func=loginCLI)

    # auth logout
    logout_parser = auth_subparsers.add_parser("logout", help="User logout")
    logout_parser.usage = "immortality auth logout [-h] [--json]"
    add_json(logout_parser)
    logout_parser.set_defaults(func=logoutCLI)

    # auth whoami
    whoami_parser = auth_subparsers.add_parser("whoami", help="查看当前登录用户")
    whoami_parser.usage = "immortality auth whoami [-h] [--json]"
    add_json(whoami_parser)
    whoami_parser.set_defaults(func=whoamiCLI)


def loginCLI(args: Namespace) -> int:
    """
    用户登录
    """
    arg_username = getattr(args, "username", None)
    arg_password = getattr(args, "password", None)
    has_username = isinstance(arg_username, str) and arg_username.strip() != ""
    has_password = isinstance(arg_password, str) and arg_password.strip() != ""

    if has_username and has_password:
        username = arg_username.strip()
        password = arg_password
    elif has_username or has_password:
        raise CLIError(
            "Either username and password are provided together, or none of them are provided",
            exit_code=2,
        )
    else:
        username = input("Username / Email: ").strip()
        if username == "":
            raise CLIError("Username / Email cannot be empty", exit_code=2)

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


def logoutCLI(args: Namespace) -> int:
    """
    用户退出登录
    """
    clearLocalSession()
    printServiceResInCLI(
        {"status": 200, "message": "Successfully logged out"},
        as_json=args.json,
    )
    return 0


def whoamiCLI(args: Namespace) -> int:
    """
    获取当前登录用户信息
    """
    user_id = getUserIdFromLocalSession()
    res = getUserById(id=user_id)
    user = res.get("user")

    if args.json:
        printServiceResInCLI(res, as_json=True)
    else:
        printTableInCLI(user)
    return 0 if res.get("status") == 200 else 1
