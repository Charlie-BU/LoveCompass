import argparse
import sys
from dotenv import load_dotenv

load_dotenv()


def parserBuilder() -> argparse.ArgumentParser:
    # 延迟导入，避免环境变量未加载
    from src.cli.utils import ImmortalityArgumentParser, ImmortalityHelpFormatter
    from src.cli.commands.index import registerTopSubparser
    from src.cli.commands.auth import registerAuthSubparser
    from src.cli.commands.fr import registerFRSubparser
    from src.cli.commands.lark_service import registerLarkServiceSubparser

    parser = ImmortalityArgumentParser(
        prog="immortality",
        formatter_class=ImmortalityHelpFormatter,
    )
    parser.usage = (
        "immortality {doctor, setup, auth, fr, lark-service} ... [-h] [--json]"
    )
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
