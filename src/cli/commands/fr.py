from argparse import Namespace, ArgumentParser, Action, _SubParsersAction
from typing import Callable
import questionary
import asyncio

from src.cli.utils import (
    CLIError,
    getUserIdFromLocalSession,
    printMarkdownInCLI,
    printServiceResInCLI,
    printTableInCLI,
)
from src.database.enums import FigureRole, Gender, MBTI, parseEnum
from src.services.figure_and_relation import (
    addFigureAndRelation,
    getAllFigureAndRelations,
    getFRAllContext,
    syncAllFeedsToFRCore,
    syncFeedsToFRCore,
)


def registerFRSubparser(
    subparsers: _SubParsersAction,
    add_json: Callable[[ArgumentParser], Action],
) -> ArgumentParser:
    """
    注册 fr 子命令
    """
    # fr
    fr_parser = subparsers.add_parser("fr", help="FigureAndRelation commands")
    fr_parser.usage = "immortality fr {add, list, show, sync-feeds} [-h]"
    fr_subparsers = fr_parser.add_subparsers(dest="fr_command")

    # fr add
    fr_create_parser = fr_subparsers.add_parser("add", help="Add FigureAndRelation")
    fr_create_parser.usage = "immortality fr add [--name <name> --gender <gender> --role <role>] [-h] [--json]"
    add_json(fr_create_parser)
    fr_create_parser.add_argument("--name", required=False, help="Figure name")
    fr_create_parser.add_argument(
        "--gender", required=False, help="Gender (male/female/other)"
    )
    fr_create_parser.add_argument(
        "--role",
        required=False,
        help="Role (self/family/friend/mentor/colleague/partner/public_figure/stranger)",
    )
    fr_create_parser.set_defaults(func=createFRCLI)

    # fr list
    fr_list_parser = fr_subparsers.add_parser(
        "list", help="List all FigureAndRelations"
    )
    fr_list_parser.usage = "immortality fr list [-h] [--json]"
    add_json(fr_list_parser)
    fr_list_parser.set_defaults(func=listAllFRsCLI)

    # fr show
    fr_show_parser = fr_subparsers.add_parser("show", help="Show full FR context")
    fr_show_parser.usage = (
        "immortality fr show --id <id> [--query <query>] [-h] [--json]"
    )
    add_json(fr_show_parser)
    fr_show_parser.add_argument(
        "--id", required=True, type=int, help="FigureAndRelation ID"
    )
    fr_show_parser.add_argument(
        "--query",
        required=False,
        help="(Optional) Recall query for fine-grained feeds (personality / interaction style / procedural info / memory detail)",
    )
    fr_show_parser.set_defaults(func=showFRCLI)

    # fr sync-feeds
    fr_sync_feeds_parser = fr_subparsers.add_parser(
        "sync-feeds",
        help="Sync fine-grained feeds (personality / interaction style / procedural info / memory detail) to FR core fields",
    )
    fr_sync_feeds_parser.usage = "immortality fr sync-feeds [--id <id>] [-h] [--json]"
    add_json(fr_sync_feeds_parser)
    fr_sync_feeds_parser.add_argument(
        "--id",
        required=False,
        type=int,
        help="(Optional) FigureAndRelation ID, sync all FRs if omitted",
    )
    fr_sync_feeds_parser.set_defaults(func=syncFeedsToFRCoreCLI)


def createFRCLI(args: Namespace) -> int:
    """
    创建 FigureAndRelation
    """

    def _resolveText(
        arg_value: str | None, label: str, required: bool = False
    ) -> str | None:
        """
        解析文本输入
        """
        if isinstance(arg_value, str) and arg_value.strip() != "":
            return arg_value.strip()
        while True:
            value = input(f"{label}: ").strip()
            if value != "":
                return value
            if required:
                print(f"{label} cannot be empty, please input again.")
                continue
            return None

    def _resolveEnum(
        arg_value: str | None,
        label: str,
        enum_values: list[str],
        allow_empty: bool = False,
    ) -> str | None:
        """
        解析枚举输入
        """
        if isinstance(arg_value, str) and arg_value.strip() != "":
            return arg_value.strip()
        choices = enum_values[:]
        if allow_empty:
            choices = ["(Skip)"] + choices

        try:
            selected = questionary.select(
                message=f"{label}:",
                choices=choices,
                use_indicator=True,
            ).ask()
        except KeyboardInterrupt as err:
            raise CLIError("Input canceled", exit_code=130) from err

        if selected is None:
            raise CLIError("Input canceled", exit_code=130)
        if allow_empty and selected == "(Skip)":
            return None
        return str(selected)

    user_id = getUserIdFromLocalSession()

    mode = "USER_INPUT"
    # 模式 1：args 提供参数
    arg_name = getattr(args, "name", None)
    arg_gender = getattr(args, "gender", None)
    arg_role = getattr(args, "role", None)
    has_name = isinstance(arg_name, str) and arg_name.strip() != ""
    has_gender = isinstance(arg_gender, str) and arg_gender.strip() != ""
    has_role = isinstance(arg_role, str) and arg_role.strip() != ""

    if all([has_name, has_gender, has_role]):
        name = arg_name.strip()
        gender = parseEnum(Gender, arg_gender.upper())
        figure_role = parseEnum(FigureRole, arg_role.upper())
        if not isinstance(gender, Gender):
            raise CLIError("Invalid gender", exit_code=2)
        if not isinstance(figure_role, FigureRole):
            raise CLIError("Invalid role", exit_code=2)
        mode = "ARGS_INPUT"
    elif any([has_name, has_gender, has_role]):
        raise CLIError(
            f"Either name, gender, and role are provided together, or none of them are provided",
            exit_code=2,
        )

    if mode == "ARGS_INPUT":
        res = addFigureAndRelation(
            user_id=user_id,
            figure_name=name,
            figure_gender=gender,
            figure_role=figure_role,
        )
    else:
        # 模式 2：用户交互输入
        name = _resolveText(getattr(args, "name", None), "Name", required=True)
        selected_gender = _resolveEnum(
            getattr(args, "gender", None),
            "Gender",
            [item.value for item in Gender],
            allow_empty=False,
        )
        gender = parseEnum(Gender, selected_gender)
        if not isinstance(gender, Gender):
            raise CLIError(
                f"Invalid gender",
                exit_code=2,
            )
        selected_role = _resolveEnum(
            getattr(args, "role", None),
            "Role",
            [item.value for item in FigureRole],
            allow_empty=False,
        )
        figure_role = parseEnum(FigureRole, selected_role)
        if not isinstance(figure_role, FigureRole):
            raise CLIError(
                f"Invalid role",
                exit_code=2,
            )
        exact_relation = _resolveText(
            getattr(args, "exact_relation", None), "Exact Relation (Optional)"
        )
        figure_mbti = None
        selected_mbti = _resolveEnum(
            getattr(args, "mbti", None),
            "MBTI (Optional)",
            [item.value for item in MBTI],
            allow_empty=True,
        )
        if selected_mbti:
            mbti = parseEnum(MBTI, selected_mbti.upper())
            if not isinstance(mbti, MBTI):
                raise CLIError(
                    f"Invalid mbti",
                    exit_code=2,
                )
            figure_mbti = mbti

        birthday = _resolveText(getattr(args, "birthday", None), "Birthday (Optional)")
        occupation = _resolveText(
            getattr(args, "occupation", None), "Occupation (Optional)"
        )
        education = _resolveText(
            getattr(args, "education", None), "Education (Optional)"
        )
        residence = _resolveText(
            getattr(args, "residence", None), "Residence (Optional)"
        )
        hometown = _resolveText(getattr(args, "hometown", None), "Hometown (Optional)")

        res = addFigureAndRelation(
            user_id=user_id,
            figure_name=name,
            figure_gender=gender,
            figure_role=figure_role,
            figure_mbti=figure_mbti,
            figure_birthday=birthday,
            figure_occupation=occupation,
            figure_education=education,
            figure_residence=residence,
            figure_hometown=hometown,
            exact_relation=exact_relation,
        )
    printServiceResInCLI(res, as_json=args.json)
    return 0 if res.get("status") == 200 else 1


def listAllFRsCLI(args: Namespace) -> int:
    user_id = getUserIdFromLocalSession()
    res = getAllFigureAndRelations(user_id=user_id)
    frs = res.get("figure_and_relations", [])

    if args.json:
        printServiceResInCLI(res, as_json=True)
    else:
        printTableInCLI(frs)

    return 0 if res.get("status") == 200 else 1


def showFRCLI(args: Namespace) -> int:
    """
    查看完整 FR 画像
    """
    user_id = getUserIdFromLocalSession()
    fr_id = getattr(args, "id", None)
    if not isinstance(fr_id, int):
        raise CLIError("Invalid fr id", exit_code=2)

    query = getattr(args, "query", None)
    if query is not None and (not isinstance(query, str) or query.strip() == ""):
        raise CLIError("query must be a non-empty string", exit_code=2)
    normalized_query = query.strip() if isinstance(query, str) else None

    res = asyncio.run(
        getFRAllContext(user_id=user_id, fr_id=fr_id, query=normalized_query)
    )
    if args.json:
        printServiceResInCLI(res, as_json=True)
        return 0 if res.get("status") == 200 else 1

    if res.get("status") != 200:
        printServiceResInCLI(res, as_json=False)
        return 1

    sections = [
        res.get("persona"),
        res.get("recalled_personality"),
        res.get("recalled_interaction_style"),
        res.get("recalled_procedural_info"),
        res.get("recalled_memory"),
    ]
    markdown_parts = [
        part.strip()
        for part in sections
        if isinstance(part, str) and part.strip() != ""
    ]
    if len(markdown_parts) == 0:
        printServiceResInCLI(
            {
                "status": 200,
                "message": "Get FigureAndRelation all context success (empty markdown)",
            },
            as_json=False,
        )
        return 0

    printMarkdownInCLI(markdown_parts)
    return 0


def syncFeedsToFRCoreCLI(args: Namespace) -> int:
    """
    同步细粒度 feeds 到 FigureAndRelation 核心字段
    """
    user_id = getUserIdFromLocalSession()
    fr_id = getattr(args, "id", None)
    if fr_id is not None:
        res = asyncio.run(syncFeedsToFRCore(user_id=user_id, fr_id=fr_id))
    else:
        res = asyncio.run(syncAllFeedsToFRCore(user_id=user_id))

    printServiceResInCLI(res, as_json=args.json)
    return 0 if res.get("status") == 200 else 1
