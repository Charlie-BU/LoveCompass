import getpass
from argparse import Namespace, ArgumentParser, Action, _SubParsersAction
from typing import Callable
import questionary

from src.cli.utils import (
    CLIError,
    getCurrentUserFromLocalSession,
    printTableInCLI,
    printServiceResInCLI,
)
from src.database.enums import Gender, parseEnum
from src.services.user import (
    getUserById,
    getUserIdByAccessToken,
    userBindLark,
    userLogin,
    userModifyPassword,
    userRegister,
)
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
    auth_parser.usage = "immortality auth {login, register, logout, whoami, modify-password, bind-lark} [-h]"
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command")

    # auth login
    login_parser = auth_subparsers.add_parser("login", help="User login")
    login_parser.usage = "immortality auth login [--username <username> --password <password>] [-h] [--json]"
    add_json(login_parser)
    login_parser.add_argument("--username", required=False, help="Username or email")
    login_parser.add_argument("--password", required=False, help="Password")
    login_parser.set_defaults(func=loginCLI)

    # auth register
    register_parser = auth_subparsers.add_parser("register", help="User register")
    register_parser.usage = (
        "immortality auth register "
        "[--username <username> --nickname <nickname> --gender <gender> --email <email> --password <password> --confirm-password <confirm_password>] "
        "[-h] [--json]"
    )
    add_json(register_parser)
    register_parser.add_argument("--username", required=False, help="Username")
    register_parser.add_argument("--nickname", required=False, help="Nickname")
    register_parser.add_argument(
        "--gender", required=False, help="Gender (male/female/other)"
    )
    register_parser.add_argument("--email", required=False, help="Email")
    register_parser.add_argument("--password", required=False, help="Password")
    register_parser.add_argument(
        "--confirm-password", required=False, help="Confirm password"
    )
    register_parser.set_defaults(func=registerCLI)

    # auth logout
    logout_parser = auth_subparsers.add_parser("logout", help="User logout")
    logout_parser.usage = "immortality auth logout [-h] [--json]"
    add_json(logout_parser)
    logout_parser.set_defaults(func=logoutCLI)

    # auth whoami
    whoami_parser = auth_subparsers.add_parser("whoami", help="Get current user info")
    whoami_parser.usage = "immortality auth whoami [-h] [--json]"
    add_json(whoami_parser)
    whoami_parser.set_defaults(func=whoamiCLI)

    # auth modify-password
    modify_password_parser = auth_subparsers.add_parser(
        "modify-password", help="Modify password for current user"
    )
    modify_password_parser.usage = "immortality auth modify-password [--old-password <old password> --new-password <new password>] [-h] [--json]"
    add_json(modify_password_parser)
    modify_password_parser.add_argument(
        "--old-password", required=False, help="Old password"
    )
    modify_password_parser.add_argument(
        "--new-password", required=False, help="New password"
    )
    modify_password_parser.set_defaults(func=modifyPasswordCLI)

    # auth bind-lark
    bind_lark_parser = auth_subparsers.add_parser(
        "bind-lark", help="Bind current user with Lark open id"
    )
    bind_lark_parser.usage = (
        "immortality auth bind-lark --lark-open-id <lark-open-id> [-h] [--json]"
    )
    add_json(bind_lark_parser)
    bind_lark_parser.add_argument("--lark-open-id", required=True, help="Lark open id")
    bind_lark_parser.set_defaults(func=bindLarkCLI)


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


def registerCLI(args: Namespace) -> int:
    """
    用户注册
    """

    def _resolveGender(
        arg_value: str | None,
    ) -> str:
        if isinstance(arg_value, str) and arg_value.strip() != "":
            return arg_value.strip()
        try:
            selected = questionary.select(
                message="Gender:",
                choices=[item.value for item in Gender],
                use_indicator=True,
            ).ask()
        except KeyboardInterrupt as err:
            raise CLIError("Input canceled", exit_code=130) from err
        if selected is None:
            raise CLIError("Input canceled", exit_code=130)
        return str(selected)

    arg_username = getattr(args, "username", None)
    arg_nickname = getattr(args, "nickname", None)
    arg_gender = getattr(args, "gender", None)
    arg_email = getattr(args, "email", None)
    arg_password = getattr(args, "password", None)
    arg_confirm_password = getattr(args, "confirm_password", None)

    has_username = isinstance(arg_username, str) and arg_username.strip() != ""
    has_nickname = isinstance(arg_nickname, str) and arg_nickname.strip() != ""
    has_gender = isinstance(arg_gender, str) and arg_gender.strip() != ""
    has_email = isinstance(arg_email, str) and arg_email.strip() != ""
    has_password = isinstance(arg_password, str) and arg_password.strip() != ""
    has_confirm_password = (
        isinstance(arg_confirm_password, str) and arg_confirm_password.strip() != ""
    )

    filled_count = sum(
        [
            has_username,
            has_nickname,
            has_gender,
            has_email,
            has_password,
            has_confirm_password,
        ]
    )
    if filled_count == 6:
        username = arg_username.strip()
        nickname = arg_nickname.strip()
        gender_raw = arg_gender.strip()
        email = arg_email.strip()
        password = arg_password
        confirm_password = arg_confirm_password
    elif filled_count == 0:
        username = input("Username: ").strip()
        nickname = input("Nickname: ").strip()
        gender_raw = _resolveGender(None)
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")
        confirm_password = getpass.getpass("Confirm password: ")
    else:
        raise CLIError(
            "Either all register args are provided together, or none of them are provided",
            exit_code=2,
        )

    if password != confirm_password:
        raise CLIError("Password and confirm password are not the same", exit_code=2)

    gender = parseEnum(Gender, gender_raw)
    if not isinstance(gender, Gender):
        raise CLIError("Invalid gender", exit_code=2)

    res = userRegister(
        username=username,
        nickname=nickname,
        gender=gender.value,
        email=email,
        password=password,
    )
    printServiceResInCLI(res, as_json=args.json)
    return 0 if res.get("status") == 200 else 1


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
    user_id = getCurrentUserFromLocalSession().get("user_id")
    res = getUserById(id=user_id)
    user = res.get("user")

    if args.json:
        printServiceResInCLI(res, as_json=True)
    else:
        printTableInCLI(user)
    return 0 if res.get("status") == 200 else 1


def modifyPasswordCLI(args: Namespace) -> int:
    """
    修改当前用户密码
    """
    user_id = getCurrentUserFromLocalSession().get("user_id")
    arg_old_password = getattr(args, "old_password", None)
    arg_new_password = getattr(args, "new_password", None)
    has_old = isinstance(arg_old_password, str) and arg_old_password.strip() != ""
    has_new = isinstance(arg_new_password, str) and arg_new_password.strip() != ""

    if has_old and has_new:
        old_password = arg_old_password
        new_password = arg_new_password
    elif has_old or has_new:
        raise CLIError(
            "Either old-password and new-password are provided together, or none of them are provided",
            exit_code=2,
        )
    else:
        old_password = getpass.getpass("Old password: ")
        new_password = getpass.getpass("New password: ")

    res = userModifyPassword(
        id=user_id,
        old_password=old_password,
        new_password=new_password,
    )
    printServiceResInCLI(res, as_json=args.json)
    return 0 if res.get("status") == 200 else 1


def bindLarkCLI(args: Namespace) -> int:
    """
    绑定飞书 open id
    """
    user_id = getCurrentUserFromLocalSession().get("user_id")
    lark_open_id = getattr(args, "lark_open_id", None)
    if not isinstance(lark_open_id, str) or lark_open_id.strip() == "":
        raise CLIError("lark-open-id is required", exit_code=2)

    res = userBindLark(user_id=user_id, lark_open_id=lark_open_id.strip())
    printServiceResInCLI(res, as_json=args.json)
    return 0 if res.get("status") == 200 else 1
