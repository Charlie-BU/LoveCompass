import re
import sys
import tomllib
import getpass
import uuid
from pathlib import Path
from argparse import Namespace, ArgumentParser, Action, _SubParsersAction
from typing import Callable
from typing import Any
from importlib import metadata
from sqlalchemy import text

from src.cli.utils import immortalityPrint, printServiceResInCLI
from src.cli.utils import CLIError
from src.database.index import session


def registerTopSubparser(
    subparsers: _SubParsersAction,
    add_json: Callable[[ArgumentParser], Action],
) -> ArgumentParser:
    """
    注册顶层子命令
    """
    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Doctor check")
    doctor_parser.usage = "immortality doctor [-h] [--json]"
    add_json(doctor_parser)
    doctor_parser.set_defaults(func=doctorCLI)

    # setup
    setup_parser = subparsers.add_parser("setup", help="Setup environment variables")
    setup_parser.usage = (
        "immortality setup "
        "[--db-user <db_user> --db-password <db_password> --db-host <db_host> --db-port <db_port> "
        "--ark-api-key <ark_api_key> "
        "--doubao-2-0-lite <endpoint_or_model_id> --doubao-2-0-mini <endpoint_or_model_id> "
        "--embedding-endpoint-id <embedding_endpoint_id> "
        "--lark-app-id <lark_bot_app_id> --lark-app-secret <lark_bot_app_secret> "
        "--lark-card-template-id <lark_card_template_id>] "
        "[-h] [--json]"
    )
    add_json(setup_parser)
    setup_parser.add_argument(
        "--db-user",
        required=False,
        help="Database user (⚠️ Attention: Must be PostgreSQL)",
    )
    setup_parser.add_argument("--db-password", required=False, help="Database password")
    setup_parser.add_argument("--db-host", required=False, help="Database host")
    setup_parser.add_argument("--db-port", required=False, help="Database port")
    setup_parser.add_argument(
        "--ark-api-key",
        required=False,
        help="ARK API key (⚠️ Attention: Must use VolcEngine Ark Service, otherwise Ark Service will not be called)",
    )
    setup_parser.add_argument(
        "--doubao-2-0-lite",
        required=False,
        help="DOUBAO_2_0_LITE endpoint_id or model_id",
    )
    setup_parser.add_argument(
        "--doubao-2-0-mini",
        required=False,
        help="DOUBAO_2_0_MINI endpoint_id or model_id (Can be the same as DOUBAO_2_0_LITE model, but not recommended)",
    )
    setup_parser.add_argument(
        "--embedding-endpoint-id",
        required=False,
        help="Embedding endpoint id",
    )
    setup_parser.add_argument("--lark-app-id", required=False, help="Lark app id")
    setup_parser.add_argument(
        "--lark-app-secret", required=False, help="Lark app secret"
    )
    setup_parser.add_argument(
        "--lark-card-template-id",
        required=False,
        help="Lark card template id (Please ask [15947513567charlie@gmail.com] for this)",
    )
    setup_parser.set_defaults(func=setupCLI)


def runDoctorCheck() -> dict[str, Any]:
    """
    执行 doctor 检查并返回结果
    """
    checks: list[dict[str, Any]] = []
    healthy = True
    guidance: list[str] = []
    project_root = Path(__file__).resolve().parents[3]
    pyproject_path = project_root / "pyproject.toml"
    env_path = project_root / ".env"

    # 1) Python 版本检查（以 pyproject.toml 的 requires-python 为准）
    python_ok = True
    python_detail = ""
    min_py = None
    requires_python = ""
    try:
        with pyproject_path.open("rb") as f:
            pyproject = tomllib.load(f)
        requires_python = str(pyproject.get("project", {}).get("requires-python", ""))
        match = re.search(r">=\s*(\d+)\.(\d+)", requires_python)
        if match:
            min_py = (int(match.group(1)), int(match.group(2)))
            current = (sys.version_info.major, sys.version_info.minor)
            python_ok = current >= min_py
            python_detail = (
                f"current={current[0]}.{current[1]}, required>={min_py[0]}.{min_py[1]}"
            )
        else:
            python_detail = f"unrecognized requires-python: {requires_python}"
    except Exception as err:
        python_ok = False
        python_detail = f"failed to parse pyproject.toml: {err}"

    checks.append({"item": "python:version", "ok": python_ok, "detail": python_detail})
    healthy = healthy and python_ok
    if not python_ok:
        guidance.append(
            "Python version does not meet requirements. Please use `>=3.13`."
        )

    # 2) .env 文件存在性与必填项完整性检查
    env_exists = env_path.exists()
    checks.append({"item": "env:file_exists", "ok": env_exists, "path": str(env_path)})
    healthy = healthy and env_exists
    if not env_exists:
        guidance.append(
            "`.env` is missing in the project root. Please create it and fill required configs."
        )

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
    env_values: dict[str, str] = {}
    if env_exists:
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped == "" or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                env_values[key.strip()] = value.strip()
        except Exception as err:
            checks.append({"item": "env:file_parse", "ok": False, "error": str(err)})
            healthy = False
            guidance.append(
                "Failed to parse `.env`. Please check the format (`KEY=VALUE`)."
            )

    missing_envs: list[str] = []
    for key in required_envs:
        value = env_values.get(key, "") if env_exists else ""
        ok = isinstance(value, str) and value.strip() != ""
        checks.append({"item": f"env:{key}", "ok": ok})
        healthy = healthy and ok
        if not ok:
            missing_envs.append(key)

    if missing_envs:
        guidance.append(
            "The following required `.env` keys are missing or empty: "
            + ", ".join(missing_envs[:10])
            + (" ..." if len(missing_envs) > 10 else "")
        )

    # 3) 依赖安装完整性检查（以 pyproject.toml 的 project.dependencies 为准）
    dependencies_ok = True
    missing_deps: list[str] = []
    dep_parse_error = None
    try:
        with pyproject_path.open("rb") as f:
            pyproject = tomllib.load(f)
        dependencies: list[str] = pyproject.get("project", {}).get("dependencies", [])
        for dep in dependencies:
            # 例：python-jose[cryptography]>=3.5.0 -> python-jose
            pkg_name = re.split(r"[<>=!~\s;]", dep, maxsplit=1)[0]
            pkg_name = pkg_name.split("[", 1)[0].strip()
            if pkg_name == "":
                continue
            try:
                metadata.version(pkg_name)
            except metadata.PackageNotFoundError:
                dependencies_ok = False
                missing_deps.append(pkg_name)
    except Exception as err:
        dependencies_ok = False
        dep_parse_error = str(err)

    checks.append(
        {
            "item": "dependencies:installed",
            "ok": dependencies_ok,
            "missing_count": len(missing_deps),
            "missing": missing_deps,
            "error": dep_parse_error,
        }
    )
    healthy = healthy and dependencies_ok
    if not dependencies_ok:
        guidance.append(
            "Dependencies are incomplete. Please run `uv sync` (or `uv pip install -e .`)."
        )

    # 4) 数据库可用性检查
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
    if not db_ok:
        guidance.append(
            "Database connection failed. Please check `DATABASE_URI`, network, and DB service status."
        )

    return {
        "status": 200 if healthy else -1,
        "message": (
            "Doctor check passed"
            if healthy
            else "Doctor check failed, please run `immortality setup` to configure environment variables"
        ),
        "checks": checks,
        "guidance": guidance,
    }


def doctorCLI(args: Namespace) -> int:
    """
    检查系统是否健康
    """
    result = runDoctorCheck()
    printServiceResInCLI(result, as_json=args.json)
    if not args.json and result.get("status") != 200:
        for idx, item in enumerate(result.get("guidance", []), start=1):
            immortalityPrint(f"[guide-{idx}] {item}", type="warning")
    return 0 if result.get("status") == 200 else 1


def setupCLI(args: Namespace) -> int:
    """
    配置环境变量
    """

    def _resolveText(arg_value: str | None, label: str) -> str:
        if isinstance(arg_value, str):
            return arg_value.strip()
        return input(f"{label}: ").strip()

    def _resolveSecret(arg_value: str | None, label: str) -> str:
        if isinstance(arg_value, str):
            return arg_value.strip()
        return getpass.getpass(f"{label}: ").strip()

    project_root = Path(__file__).resolve().parents[3]
    env_example_path = project_root / ".env.example"
    env_path = project_root / ".env"

    if not env_example_path.exists():
        raise CLIError("`.env.example` not found in project root", exit_code=1)

    arg_db_user = getattr(args, "db_user", None)
    arg_db_password = getattr(args, "db_password", None)
    arg_db_host = getattr(args, "db_host", None)
    arg_db_port = getattr(args, "db_port", None)
    arg_ark_api_key = getattr(args, "ark_api_key", None)
    arg_doubao_2_0_lite = getattr(args, "doubao_2_0_lite", None)
    arg_doubao_2_0_mini = getattr(args, "doubao_2_0_mini", None)
    arg_embedding_endpoint_id = getattr(args, "embedding_endpoint_id", None)
    arg_lark_app_id = getattr(args, "lark_app_id", None)
    arg_lark_app_secret = getattr(args, "lark_app_secret", None)
    arg_lark_card_template_id = getattr(args, "lark_card_template_id", None)

    db_user = _resolveText(arg_db_user, "db_user")
    db_password = _resolveSecret(arg_db_password, "db_password")
    db_host = _resolveText(arg_db_host, "db_host")
    db_port = _resolveText(arg_db_port, "db_port")
    login_secret = uuid.uuid4().hex
    ark_api_key = _resolveSecret(arg_ark_api_key, "ark_api_key")
    doubao_2_0_lite = _resolveText(
        arg_doubao_2_0_lite, "doubao_2_0_lite_endpoint_or_model_id"
    )
    doubao_2_0_mini = _resolveText(
        arg_doubao_2_0_mini, "doubao_2_0_mini_endpoint_or_model_id"
    )
    embedding_endpoint_id = _resolveText(
        arg_embedding_endpoint_id, "embedding_endpoint_id"
    )
    lark_app_id = _resolveText(arg_lark_app_id, "lark_bot_app_id")
    lark_app_secret = _resolveSecret(arg_lark_app_secret, "lark_bot_app_secret")
    lark_card_template_id = _resolveText(
        arg_lark_card_template_id, "lark_card_template_id"
    )

    values = {
        "db_user": db_user,
        "db_password": db_password,
        "db_host": db_host,
        "db_port": db_port,
        "login_secret": login_secret,
        "ark_api_key": ark_api_key,
        "doubao_2_0_lite_endpoint_or_model_id": doubao_2_0_lite,
        "doubao_2_0_mini_endpoint_or_model_id": doubao_2_0_mini,
        "embedding_endpoint_id": embedding_endpoint_id,
        "lark_bot_app_id": lark_app_id,
        "lark_bot_app_secret": lark_app_secret,
        "lark_card_template_id": lark_card_template_id,
    }

    template = env_example_path.read_text(encoding="utf-8")
    output = template
    for key, value in values.items():
        output = output.replace(f"<{key}>", value)

    env_path.write_text(output, encoding="utf-8")

    printServiceResInCLI(
        {
            "status": 200,
            "message": f"Environment variables are configured successfully, please run `immortality doctor` to check",
            "env_path": str(env_path),
        },
        as_json=args.json,
    )
    return 0
