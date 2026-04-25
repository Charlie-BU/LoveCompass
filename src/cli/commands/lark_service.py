from argparse import Namespace, ArgumentParser, Action, _SubParsersAction
from typing import Callable

from src.cli.commands.index import runDoctorCheck
from src.cli.utils import immortalityPrint, printServiceResInCLI


def registerLarkServiceSubparser(
    subparsers: _SubParsersAction,
    add_json: Callable[[ArgumentParser], Action],
) -> ArgumentParser:
    """
    注册 lark-service 子命令
    """
    lark_service_parser = subparsers.add_parser(
        "lark-service", help="Lark service commands"
    )
    lark_service_parser.usage = "immortality lark-service start [-h] [--json]"
    lark_service_subparsers = lark_service_parser.add_subparsers(
        dest="lark_service_command"
    )

    start_parser = lark_service_subparsers.add_parser(
        "start", help="Start lark websocket service"
    )
    start_parser.usage = "immortality lark-service start [-h] [--json]"
    add_json(start_parser)
    start_parser.set_defaults(func=startLarkServiceCLI)


def startLarkServiceCLI(args: Namespace) -> int:
    """
    启动 lark 服务（先执行 doctor，通过后才启动）
    """
    from src.main import main

    doctor_result = runDoctorCheck()
    if doctor_result.get("status") != 200:
        printServiceResInCLI(doctor_result, as_json=args.json)
        if not args.json:
            for idx, guide in enumerate(doctor_result.get("guidance", []), start=1):
                immortalityPrint(f"[guide-{idx}] {guide}", type="warning")
        return 1

    immortalityPrint("Doctor check passed. Starting lark service...", type="success")
    main()
    return 0
