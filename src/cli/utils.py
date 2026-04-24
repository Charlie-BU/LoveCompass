import json
from typing import Any, Literal
from tabulate import tabulate

from src.services.user import getUserIdByAccessToken
from src.cli.session import clearLocalSession, loadLocalSession
from src.utils.index import stringifyValue


class CLIError(Exception):
    """
    CLI 错误异常
    """

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def immortalityPrint(
    message: str,
    type: Literal["success", "info", "warning", "error", "default"] = "info",
) -> None:
    """
    Immortality 打印，支持不同颜色的输出
    """
    color_map = {
        "success": "\033[92m",  # green
        "info": "\033[94m",  # blue
        "warning": "\033[93m",  # yellow
        "error": "\033[91m",  # red
        "default": "",
    }
    reset = "\033[0m"  # 输出后追加 reset，避免影响后续终端输出
    color = color_map.get(type, "")
    print(f"『Immortality』{color}{message}{reset}")


def printServiceResInCLI(data: dict[str, Any], as_json: bool) -> None:
    """
    打印 service 响应，支持 JSON 输出
    """
    if as_json:
        # 打印 data 全量内容
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    # 只打印 message
    status = data.get("status")
    message = data.get("message", "")
    label = None
    if status >= 200:
        label = "success"
    else:
        label = "error"
    immortalityPrint(f"[{label}] {message}", type=label)


def printDictAsTableInCLI(data: dict[str, Any]) -> None:
    """
    将字典渲染为表格打印
    """

    rows = [[str(key), stringifyValue(value)] for key, value in data.items()]
    print(f"\n{tabulate(rows, headers=["Field", "Value"], tablefmt="github")}\n")


def getUserIdFromLocalSession() -> int:
    """
    从本地 session 中校验登录态并获取 user_id
    """
    current_session = loadLocalSession()
    token = current_session.get("access_token")
    if not isinstance(token, str) or token.strip() == "":
        clearLocalSession()
        raise CLIError(
            message="Please login first via `immortality auth login`", exit_code=2
        )
    try:
        return getUserIdByAccessToken(token=token)
    except Exception:
        clearLocalSession()
        raise CLIError("Your login session is expired, please login again", exit_code=3)
