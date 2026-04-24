from argparse import Namespace, ArgumentParser, Action, _SubParsersAction
from typing import Callable

from src.cli.utils import (
    CLIError,
    getUserIdFromLocalSession,
    printServiceResInCLI,
)
from src.database.enums import FigureRole, Gender, MBTI, parseEnum
from src.services.figure_and_relation import (
    addFigureAndRelation,
    getAllFigureAndRelations,
)


def frParserBuilder(
    subparsers: _SubParsersAction,
    add_json: Callable[[ArgumentParser], Action],
) -> ArgumentParser:
    """
    构建 fr 子命令解析器
    """
    # fr
    fr_parser = subparsers.add_parser("fr", help="FigureAndRelation 相关命令")
    fr_parser.usage = "immortality fr {create, list} [-h]"
    fr_subparsers = fr_parser.add_subparsers(dest="fr_command")

    fr_create_parser = fr_subparsers.add_parser("create", help="创建 FR")
    fr_create_parser.usage = (
        "immortality fr create --name NAME --gender GENDER --role ROLE "
        "[--mbti MBTI] [--birthday BIRTHDAY] [--occupation OCCUPATION] "
        "[--education EDUCATION] [--residence RESIDENCE] [--hometown HOMETOWN] "
        "[--exact-relation EXACT_RELATION] [-h] [--json]"
    )
    add_json(fr_create_parser)
    fr_create_parser.add_argument("--name", required=True, help="人物姓名")
    fr_create_parser.add_argument(
        "--gender", required=True, help="性别（male/female/other）"
    )
    fr_create_parser.add_argument(
        "--role",
        required=True,
        help="角色（self/family/friend/mentor/colleague/partner/public_figure/stranger）",
    )
    fr_create_parser.add_argument("--mbti", required=False, help="MBTI（如 ENTJ）")
    fr_create_parser.add_argument("--birthday", required=False, help="生日")
    fr_create_parser.add_argument("--occupation", required=False, help="职业")
    fr_create_parser.add_argument("--education", required=False, help="教育背景")
    fr_create_parser.add_argument("--residence", required=False, help="常住地")
    fr_create_parser.add_argument("--hometown", required=False, help="家乡")
    fr_create_parser.add_argument(
        "--exact-relation", required=False, help="精确关系描述"
    )
    fr_create_parser.set_defaults(func=FRCreateCMD)

    fr_list_parser = fr_subparsers.add_parser("list", help="查看全部 FR")
    fr_list_parser.usage = "immortality fr list [-h] [--json]"
    add_json(fr_list_parser)
    fr_list_parser.set_defaults(func=FRListCMD)


def FRCreateCMD(args: Namespace) -> int:
    user_id = getUserIdFromLocalSession()

    gender = parseEnum(Gender, args.gender)
    if not isinstance(gender, Gender):
        raise CLIError(
            f"无效 gender：{args.gender}，可选值：{', '.join([g.value for g in Gender])}",
            exit_code=2,
        )

    figure_role = parseEnum(FigureRole, args.role)
    if not isinstance(figure_role, FigureRole):
        raise CLIError(
            f"无效 role：{args.role}，可选值：{', '.join([r.value for r in FigureRole])}",
            exit_code=2,
        )

    figure_mbti = None
    if args.mbti:
        mbti = parseEnum(MBTI, args.mbti.upper())
        if not isinstance(mbti, MBTI):
            raise CLIError(
                f"无效 mbti：{args.mbti}，可选值：{', '.join([m.value for m in MBTI])}",
                exit_code=2,
            )
        figure_mbti = mbti

    result = addFigureAndRelation(
        user_id=user_id,
        figure_name=args.name,
        figure_gender=gender,
        figure_role=figure_role,
        figure_mbti=figure_mbti,
        figure_birthday=args.birthday,
        figure_occupation=args.occupation,
        figure_education=args.education,
        figure_residence=args.residence,
        figure_hometown=args.hometown,
        exact_relation=args.exact_relation,
    )
    printServiceResInCLI(result, as_json=args.json)
    return 0 if result.get("status") == 200 else 1


def FRListCMD(args: Namespace) -> int:
    user_id = getUserIdFromLocalSession()
    result = getAllFigureAndRelations(user_id=user_id)
    printServiceResInCLI(result, as_json=args.json)
    return 0 if result.get("status") == 200 else 1
