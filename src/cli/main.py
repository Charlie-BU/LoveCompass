import argparse
import re
import sys
from dotenv import load_dotenv

from src.cli.constants import (
    ANSI_RESET,
    WELCOME_BANNER,
    IMMORTALITY_LOGO,
    ANSI_ORANGE,
    ANSI_WHITE,
    ANSI_DIM,
    ANSI_BOLD,
)

load_dotenv()


class ImmortalityHelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        colored_heading = f"{ANSI_ORANGE}{ANSI_BOLD}{heading}{ANSI_RESET}"
        super().start_section(colored_heading)


def _colorizeHelpColumns(help_text: str) -> str:
    """
    在不影响 argparse 对齐的前提下，对左列命令和右列说明做后处理着色
    """
    lines = help_text.splitlines()
    colored_lines: list[str] = []
    # 匹配形如：<indent><left><2+ spaces><right>
    row_pattern = re.compile(r"^(\s*)(\S.*?)(\s{2,})(\S.*)$")

    for line in lines:
        matched = row_pattern.match(line)
        if not matched:
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


def parserBuilder() -> argparse.ArgumentParser:
    # 延迟导入，避免环境变量未加载
    from src.cli.commands.auth import registerAuthSubparser
    from src.cli.commands.fr import registerFRSubparser
    from src.cli.commands.index import registerTopSubparser
    from src.cli.commands.lark_service import registerLarkServiceSubparser

    parser = ImmortalityArgumentParser(
        prog="immortality",
        formatter_class=ImmortalityHelpFormatter,
    )
    parser.usage = "immortality {doctor, auth, fr, lark-service} ... [-h] [--json]"
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    subparsers = parser.add_subparsers(dest="command")
    add_json = lambda p: p.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    registerTopSubparser(subparsers, add_json)
    registerAuthSubparser(subparsers, add_json)
    registerFRSubparser(subparsers, add_json)
    registerLarkServiceSubparser(subparsers, add_json)

    return parser


def main() -> int:
    """
    CLI 入口
    返回退出码：0 成功，其他值为失败
    """
    # 延迟导入，避免环境变量未加载
    from src.cli.utils import CLIError, immortalityPrint

    try:
        parser = parserBuilder()
        args = parser.parse_args()

        if not hasattr(args, "func"):
            parser.print_help()
            return 1

        return int(args.func(args))
    except KeyboardInterrupt:
        print("\n")
        immortalityPrint("Exited by user", type="warning")
        return 130
    except CLIError as err:
        immortalityPrint(err, type="warning")
        return err.exit_code
    except Exception as err:
        immortalityPrint(f"Unexpected error: {err}", type="error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
