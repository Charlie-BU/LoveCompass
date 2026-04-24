import argparse
import sys
from dotenv import load_dotenv


load_dotenv()


def parserBuilder() -> argparse.ArgumentParser:
    # 延迟导入，避免环境变量未加载
    from src.cli.commands.auth import authParserBuilder
    from src.cli.commands.fr import frParserBuilder
    from src.cli.commands.index import topSubparserBuilder

    parser = argparse.ArgumentParser(prog="immortality")
    parser.usage = "immortality {doctor, auth, fr} ... [-h] [--json]"
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")

    subparsers = parser.add_subparsers(dest="command")
    add_json = lambda p: p.add_argument(
        "--json", action="store_true", help="以 JSON 格式输出结果"
    )

    topSubparserBuilder(subparsers, add_json)
    authParserBuilder(subparsers, add_json)
    frParserBuilder(subparsers, add_json)

    return parser


def main() -> int:
    """
    CLI 入口
    返回退出码：0 成功，其他值为失败
    """
    # 延迟导入，避免环境变量未加载
    from src.cli.utils import CLIError, immortalityPrint

    parser = parserBuilder()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    try:
        return int(args.func(args))
    except CLIError as err:
        immortalityPrint(err, type="warning")
        return err.exit_code
    except Exception as err:
        immortalityPrint(f"Unexpected error: {err}", type="error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
