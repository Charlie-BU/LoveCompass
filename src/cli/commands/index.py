import os
from argparse import Namespace, ArgumentParser, Action, _SubParsersAction
from typing import Callable
from typing import Any
from sqlalchemy import text

from src.cli.utils import printServiceResInCLI
from src.database.index import session


def topSubparserBuilder(
    subparsers: _SubParsersAction,
    add_json: Callable[[ArgumentParser], Action],
) -> ArgumentParser:
    """
    构建顶层子命令解析器
    """
    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Doctor check")
    doctor_parser.usage = "immortality doctor [-h] [--json]"
    add_json(doctor_parser)
    doctor_parser.set_defaults(func=doctorCMD)


def doctorCMD(args: Namespace) -> int:
    """
    检查系统是否健康
    """
    checks: list[dict[str, Any]] = []
    healthy = True

    required_envs = [
        "DATABASE_URI",
        "CHECKPOINT_DATABASE_URI",
        "ALGORITHM",
        "LOGIN_SECRET",
        "ARK_BASE_URL",
        "ARK_API_KEY",
        "DOUBAO_2_0_LITE",
        "DOUBAO_2_0_MINI",
        "EMBEDDING_MODEL_NAME",
        "EMBEDDING_BASE_URL",
        "EMBEDDING_ENDPOINT_ID",
        "LARK_APP_ID",
        "LARK_APP_SECRET",
        "LARK_CARD_TEMPLATE_ID",
        "FR_BUILDING_PREPROCESS",
        "FR_BUILDING_EXTRACT_FR_INTRINSIC_CANDIDATES",
        "FR_BUILDING_COMPARE_FIELD",
        "FR_BUILDING_COLLEAGUE",
        "FR_BUILDING_FAMILY",
        "FR_BUILDING_FRIEND",
        "FR_BUILDING_MENTOR",
        "FR_BUILDING_PARTNER",
        "FR_BUILDING_PUBLIC_FIGURE",
        "FR_BUILDING_SELF",
        "FR_BUILDING_PERSONALITY",
        "FR_BUILDING_INTERACTION_STYLE",
        "FR_BUILDING_PROCEDURAL_INFO",
        "FR_BUILDING_MEMORY",
        "FR_BUILDING_REPORT",
        "SYNC_PERSONALITY_FEEDS_TO_FR_CORE",
        "SYNC_INTERACTION_FEEDS_TO_FR_CORE",
        "SYNC_PROCEDURAL_FEEDS_TO_FR_CORE",
        "SYNC_MEMORY_FEEDS_TO_FR_CORE",
        "SUMMARY_MESSAGES_FOR_TRIM",
        "CONVERSATION_SYSTEM_PROMPT",
        "SHORT_TERM_MEMORY_MAX_CHARS",
        "SHORT_TERM_MEMORY_TARGET_CHARS",
        "SHORT_TERM_MEMORY_MAX_MESSAGES",
        "TOP_K_FEEDS_FOR_COMPARE",
        "TOP_K_PERSONALITY_FEEDS_FOR_CONVERSATION",
        "TOP_K_INTERACTION_FEEDS_FOR_CONVERSATION",
        "TOP_K_PROCEDURAL_FEEDS_FOR_CONVERSATION",
        "TOP_K_MEMORY_FEEDS_FOR_CONVERSATION",
        "TOP_K_PERSONALITY_FEEDS_FOR_CORE_SYNC",
        "TOP_K_INTERACTION_FEEDS_FOR_CORE_SYNC",
        "TOP_K_PROCEDURAL_FEEDS_FOR_CORE_SYNC",
        "TOP_K_MEMORY_FEEDS_FOR_CORE_SYNC",
        "VECTOR_CANDIDATES",
        "HALF_LIFE_DAYS",
        "MAX_WORDS_TO_AND_FROM_FIGURE",
        "WAITING_SECONDS_FOR_CONVERSATION",
    ]
    for key in required_envs:
        value = os.getenv(key)
        ok = isinstance(value, str) and value.strip() != ""
        checks.append({"item": f"env:{key}", "ok": ok})
        healthy = healthy and ok

    db_ok = True
    db_error = None
    try:
        with session() as db:
            db.execute(text("SELECT 1"))
    except Exception as err:
        db_ok = False
        db_error = str(err)
        healthy = False

    checks.append({"item": "database:connectivity", "ok": db_ok, "error": db_error})
    result = {
        "status": 200 if healthy else -1,
        "message": "Doctor check passed" if healthy else "Doctor check failed",
        "checks": checks,
    }
    printServiceResInCLI(result, as_json=args.json)
    return 0 if healthy else 1
