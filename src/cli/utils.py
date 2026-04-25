import argparse
import json
import re
from typing import Any, Literal
from tabulate import tabulate
from rich.console import Console
from rich.markdown import Markdown

from src.utils.index import stringifyValue
from src.services.user import getUserIdByAccessToken
from src.cli.session import clearLocalSession, loadLocalSession
from src.cli.constants import (
    ANSI_BLUE,
    ANSI_BOLD,
    ANSI_DIM,
    ANSI_GREEN,
    ANSI_ORANGE,
    ANSI_RED,
    ANSI_RESET,
    ANSI_WHITE,
    ANSI_YELLOW,
    IMMORTALITY_LOGO,
    WELCOME_BANNER,
)


class CLIError(Exception):
    """
    CLI 错误异常
    """

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class ImmortalityHelpFormatter(argparse.HelpFormatter):
    """
    自定义 argparse 帮助格式化器，用于着色命令和说明
    """

    def start_section(self, heading):
        colored_heading = f"{ANSI_ORANGE}{ANSI_BOLD}{heading}{ANSI_RESET}"
        super().start_section(colored_heading)

    def _format_action(self, action):
        # Hide the aggregated subparser metavar line like "{a,b,c}" while
        # keeping each sub-command row under "positional arguments".
        if isinstance(action, argparse._SubParsersAction):
            parts = []
            for subaction in self._iter_indented_subactions(action):
                parts.append(self._format_action(subaction))
            return self._join_parts(parts)
        return super()._format_action(action)


def _colorizeHelpColumns(help_text: str) -> str:
    """
    在不影响 argparse 对齐的前提下，对左列命令和右列说明做后处理着色
    """
    lines = help_text.splitlines()
    colored_lines: list[str] = []
    # 匹配形如：<indent><left><2+ spaces><right>
    row_pattern = re.compile(r"^(\s*)(\S.*?)(\s{2,})(\S.*)$")
    # 匹配只有左列的 option 行（说明在下一行）
    option_only_pattern = re.compile(r"^(\s*)((?:-\w|--)[^\s].*)$")

    for line in lines:
        matched = row_pattern.match(line)
        if not matched:
            option_only = option_only_pattern.match(line)
            if option_only:
                indent, left = option_only.groups()
                colored_lines.append(
                    f"{indent}{ANSI_ORANGE}{ANSI_BOLD}{left}{ANSI_RESET}"
                )
                continue
            colored_lines.append(line)
            continue

        indent, left, gap, right = matched.groups()
        # 跳过 usage 行，避免重复着色
        if left.lower().startswith("usage:"):
            colored_lines.append(line)
            continue

        colored_lines.append(
            f"{indent}{ANSI_ORANGE}{ANSI_BOLD}{left}{ANSI_RESET}"
            f"{gap}{ANSI_WHITE}{right}{ANSI_RESET}"
        )

    return "\n".join(colored_lines)


class ImmortalityArgumentParser(argparse.ArgumentParser):
    """
    自定义 argparse 解析器，用于着色命令和说明
    """

    def format_help(self):
        help_text = super().format_help()
        help_text = _colorizeHelpColumns(help_text)
        help_text = help_text.replace(
            "usage:",
            f"{ANSI_ORANGE}{ANSI_BOLD}Usage:{ANSI_RESET}",
            1,
        )
        hint = f"{ANSI_DIM}Hint: run `<command> --help` for more details.{ANSI_RESET}"
        return f"{WELCOME_BANNER}\n\n{IMMORTALITY_LOGO}\n{help_text}\n{hint}\n"


def immortalityPrint(
    message: str,
    type: Literal["success", "info", "warning", "error", "default"] = "info",
) -> None:
    """
    Immortality 打印，支持不同颜色的输出
    """
    color_map = {
        "success": ANSI_GREEN,
        "info": ANSI_BLUE,
        "warning": ANSI_YELLOW,
        "error": ANSI_RED,
        "default": ANSI_RESET,
    }
    reset = ANSI_RESET  # 输出后追加 reset，避免影响后续终端输出
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


def printTableInCLI(data: dict[str, Any] | list[dict[str, Any]]) -> None:
    """
    将字典或对象数组渲染为表格打印
    """
    if isinstance(data, dict):
        rows = [[str(key), stringifyValue(value)] for key, value in data.items()]
        table = tabulate(rows, headers=["Field", "Value"], tablefmt="github")
        print(f"\n{table}\n")
        return

    if isinstance(data, list):
        if len(data) == 0:
            immortalityPrint("[info] Empty list", type="info")
            return

        # 仅支持对象数组；若元素不是对象则回退为单列表展示
        if not all(isinstance(item, dict) for item in data):
            rows = [[stringifyValue(item)] for item in data]
            table = tabulate(rows, headers=["Value"], tablefmt="github")
            print(f"\n{table}\n")
            return

        headers: list[str] = []
        for item in data:
            for key in item.keys():
                key_str = str(key)
                if key_str not in headers:
                    headers.append(key_str)

        rows = [
            [stringifyValue(item.get(header)) for header in headers] for item in data
        ]
        table = tabulate(rows, headers=headers, tablefmt="github")
        print(f"\n{table}\n")


def printMarkdownInCLI(markdown_text: str | list[str]) -> None:
    """
    渲染 markdown 内容并输出到 CLI
    """
    if isinstance(markdown_text, list):
        parts = [
            part.strip()
            for part in markdown_text
            if isinstance(part, str) and part.strip() != ""
        ]
        if len(parts) == 0:
            immortalityPrint("[info] Empty markdown", type="info")
            return
        content = "\n\n---\n\n".join(parts)
    else:
        content = markdown_text.strip() if isinstance(markdown_text, str) else ""
        if content == "":
            immortalityPrint("[info] Empty markdown", type="info")
            return

    console = Console()
    console.print(Markdown(content))


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
