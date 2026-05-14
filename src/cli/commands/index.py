import re
import sys
import getpass
import uuid
import time
import subprocess
from pathlib import Path
from argparse import Namespace, ArgumentParser, Action, _SubParsersAction
from typing import Callable, Any
from importlib import metadata, resources
import questionary
from datetime import datetime

from src.cli.utils import immortalityPrint, printServiceResInCLI
from src.cli.utils import CLIError
from src.cli.constants import (
    IMMORTALITY_HOME_DIR,
    IMMORTALITY_ENV_PATH,
)
from src.database.models import initDatabaseIfNeeded
from src.utils.request import fetch


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
        "--embedding-endpoint-id <embedding_model_endpoint_or_model_id> "
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
        help="LITE_MODEL endpoint_id or model_id",
    )
    setup_parser.add_argument(
        "--doubao-2-0-mini",
        required=False,
        help="MINI_MODEL endpoint_id or model_id (Can be the same as LITE_MODEL model, but not recommended)",
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
        help="Lark card template id",
    )
    setup_parser.set_defaults(func=setupCLI)

    # logs
    logs_parser = subparsers.add_parser("logs", help="View logs dynamically")
    logs_parser.usage = "immortality logs [--date <YYYYMMDD>] [-h]"
    logs_parser.add_argument(
        "--date",
        required=False,
        help="Log date in YYYYMMDD format, defaults to today",
    )
    logs_parser.set_defaults(func=logsCLI)


def runDoctorCheck() -> dict[str, Any]:
    """
    执行 doctor 检查并返回结果
    """
    checks: list[dict[str, Any]] = []
    healthy = True
    guidance: list[str] = []
    env_path = IMMORTALITY_ENV_PATH

    # 1) Python 版本检查
    python_ok = True
    python_detail = ""
    min_py = (3, 12)
    current = (sys.version_info.major, sys.version_info.minor)
    python_ok = current >= min_py
    python_detail = (
        f"current={current[0]}.{current[1]}, required>={min_py[0]}.{min_py[1]}"
    )

    checks.append({"item": "python:version", "ok": python_ok, "detail": python_detail})
    healthy = healthy and python_ok
    if not python_ok:
        guidance.append(
            "Python version does not meet requirements. Please use `>=3.12`."
        )

    # 2) .env 文件存在性与必填项完整性检查
    env_exists = env_path.exists()
    checks.append({"item": "env:file_exists", "ok": env_exists, "path": str(env_path)})
    healthy = healthy and env_exists
    if not env_exists:
        guidance.append(
            "`.env` is missing in ~/.immortality/.env. Please run `immortality setup` first."
        )

    required_envs = [
        "USE_SHARED_DATABASE",
        "DATABASE_URI",
        "CHECKPOINT_DATABASE_URI",
        "ALGORITHM",
        "LOGIN_SECRET",
        "ARK_BASE_URL",
        "ARK_API_KEY",
        "LITE_MODEL",
        "MINI_MODEL",
        "EMBEDDING_MODEL_NAME",
        "EMBEDDING_BASE_URL",
        "EMBEDDING_MODEL",
        "LARK_APP_ID",
        "LARK_APP_SECRET",
        "LARK_CARD_TEMPLATE_ID",
        "HTTP_BASE_URL",
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

    use_shared_database = False
    use_shared_database_raw = ""
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

        use_shared_database_raw = (
            env_values.get("USE_SHARED_DATABASE", "") or ""
        ).strip()
        if use_shared_database_raw.lower() == "true":
            use_shared_database = True
            checks.append(
                {
                    "item": "env:USE_SHARED_DATABASE",
                    "ok": True,
                    "value": use_shared_database_raw,
                }
            )
        elif use_shared_database_raw.lower() == "false":
            checks.append(
                {
                    "item": "env:USE_SHARED_DATABASE",
                    "ok": True,
                    "value": use_shared_database_raw or "False",
                }
            )
        else:
            checks.append(
                {
                    "item": "env:USE_SHARED_DATABASE",
                    "ok": False,
                    "error": "Invalid value",
                    "value": use_shared_database_raw,
                }
            )
            healthy = False
            guidance.append(
                "Invalid USE_SHARED_DATABASE value. Please re-run `immortality setup`."
            )

    required_envs_to_check = required_envs
    if use_shared_database:
        required_envs_to_check = [
            key
            for key in required_envs
            if key not in {"DATABASE_URI", "CHECKPOINT_DATABASE_URI"}
        ]
    else:
        required_envs_to_check = [
            key for key in required_envs if key != "HTTP_BASE_URL"
        ]

    missing_envs: list[str] = []
    for key in required_envs_to_check:
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

    # 3) 依赖安装完整性检查（优先使用已安装包元数据）
    dependencies_ok = True
    missing_deps: list[str] = []
    dep_parse_error = None
    try:
        dependencies: list[str] = metadata.requires("digital-immortality") or []
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
    except metadata.PackageNotFoundError:
        # 开发态可能未安装为分发包，此时跳过依赖元数据检查
        dependencies_ok = True
        dep_parse_error = "distribution metadata not found, dependency check skipped"
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

    # 4) 数据库可用性 / 远端服务连通性检查
    if use_shared_database:
        http_base_url = (env_values.get("HTTP_BASE_URL", "") or "").strip().rstrip("/")
        ping_ok = False
        ping_error = None
        ping_response: Any = None
        if http_base_url:
            try:
                ping_response = fetch(
                    f"{http_base_url}/ping",
                    method="GET",
                    timeout=10,
                    raise_for_status=True,
                )
                ping_ok = ping_response.get("body") == "pong"
                if not ping_ok:
                    ping_error = (
                        f"Unexpected response body: {ping_response.get('body')!r}"
                    )
            except Exception as err:
                ping_error = str(err)
        else:
            ping_error = "HTTP_BASE_URL is empty"

        checks.append(
            {
                "item": "remote_service:ping",
                "ok": ping_ok,
                "url": f"{http_base_url}/ping" if http_base_url else "",
                "response": ping_response,
                "error": ping_error,
            }
        )
        healthy = healthy and ping_ok
        if not ping_ok:
            guidance.append(
                "Shared database mode requires a reachable server. Please contact the server administrator to check `HTTP_BASE_URL` and the server is reachable."
            )

    else:
        db_ok = True
        db_error = None
        try:
            from src.database.index import (
                checkDatabaseConnection,
            )  # 只用来检查数据库连接

            checkDatabaseConnection()
        except Exception as err:
            db_ok = False
            db_error = str(err)
            healthy = False

        checks.append({"item": "database:connectivity", "ok": db_ok, "error": db_error})
        if not db_ok:
            guidance.append(
                "Database connection failed. Please check `DATABASE_URI`, network, and DB service status. "
                "If you selected Docker mode in setup, ensure postgres container is running."
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


def _checkDocker() -> list[str] | None:
    """
    检查 Docker 是否正常工作
    """
    # 检查 docker 命令
    try:
        docker_check = subprocess.run(
            ["docker", "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as err:
        raise CLIError(
            "Docker command not found. Please install Docker Desktop first.",
            exit_code=1,
        ) from err
    if docker_check.returncode != 0:
        raise CLIError(
            f"Docker is unavailable: {(docker_check.stderr or docker_check.stdout).strip()}",
            exit_code=1,
        )

    # 检查 docker compose 命令
    compose_cmd: list[str] | None = None
    compose_check = subprocess.run(
        ["docker", "compose", "version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if compose_check.returncode == 0:
        compose_cmd = ["docker", "compose"]
    else:
        try:
            legacy_compose_check = subprocess.run(
                ["docker-compose", "--version"],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            legacy_compose_check = None
        if legacy_compose_check and legacy_compose_check.returncode == 0:
            compose_cmd = ["docker-compose"]

    if compose_cmd is None:
        raise CLIError(
            "`docker compose` and `docker-compose` are both unavailable. "
            "Please install Docker Compose first.",
            exit_code=1,
        )
    return compose_cmd


def _setupCheckpointsDBIfNeeded():
    """
    配置 immortality_checkpoints 数据库
    """
    # 检查 immortality_checkpoints 数据库是否存在
    check_checkpoint_db = subprocess.run(
        [
            "docker",
            "exec",
            "immortality-postgres",
            "psql",
            "-h",
            "127.0.0.1",
            "-U",
            "immortality",
            "-d",
            "immortality",
            "-tAc",
            "SELECT 1 FROM pg_database WHERE datname = 'immortality_checkpoints';",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if check_checkpoint_db.returncode != 0:
        raise CLIError(
            "PostgreSQL is running but failed to check `immortality_checkpoints` database: "
            + (check_checkpoint_db.stderr or check_checkpoint_db.stdout).strip(),
            exit_code=1,
        )
    checkpoint_exists = check_checkpoint_db.stdout.strip() == "1"

    if not checkpoint_exists:
        create_checkpoint_db = subprocess.run(
            [
                "docker",
                "exec",
                "immortality-postgres",
                "psql",
                "-h",
                "127.0.0.1",
                "-U",
                "immortality",
                "-d",
                "immortality",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                "CREATE DATABASE immortality_checkpoints;",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if create_checkpoint_db.returncode != 0:
            raise CLIError(
                "PostgreSQL is running but failed to create `immortality_checkpoints` database: "
                + (create_checkpoint_db.stderr or create_checkpoint_db.stdout).strip(),
                exit_code=1,
            )


def dockerDBSteup() -> dict[str, str]:
    """
    通过 Docker 配置 PostgreSQL 数据库
    """
    docker_compose_path = IMMORTALITY_HOME_DIR / "docker-compose.yml"
    docker_init_sql_path = IMMORTALITY_HOME_DIR / "init-db.sh"

    # 检查 Docker 是否正常工作
    compose_cmd = _checkDocker()

    # 加载 docker-compose.yml 模板
    try:
        compose_template = (
            resources.files("src.cli")
            .joinpath("assets/docker-compose.yml")
            .read_text(encoding="utf-8")
        )
    except Exception as err:
        raise CLIError(
            f"Cannot load docker-compose template from package: {err}",
            exit_code=1,
        ) from err
    try:
        init_db_sql = (
            resources.files("src.cli")
            .joinpath("assets/init-db.sh")
            .read_text(encoding="utf-8")
        )
    except Exception as err:
        raise CLIError(
            f"Cannot load init-db.sh template from package: {err}",
            exit_code=1,
        ) from err

    try:
        docker_compose_path.write_text(compose_template, encoding="utf-8")
        docker_init_sql_path.write_text(init_db_sql, encoding="utf-8")
    except OSError as err:
        raise CLIError(
            f"Cannot write docker assets into `{IMMORTALITY_HOME_DIR}`: {err}",
            exit_code=1,
        ) from err

    # 检查完毕，启动 PostgreSQL 容器
    immortalityPrint(
        "Starting PostgreSQL with docker compose, please wait...", type="info"
    )
    compose_up = subprocess.run(
        compose_cmd
        + [
            "-f",
            str(docker_compose_path),
            "up",
            "-d",
            "postgres",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if compose_up.returncode != 0:
        raise CLIError(
            "Failed to start PostgreSQL container with docker compose: "
            + (compose_up.stderr or compose_up.stdout).strip(),
            exit_code=1,
        )

    wait_seconds = 50
    db_ready = False
    for _ in range(wait_seconds):
        pg_ready_check = subprocess.run(
            [
                "docker",
                "exec",
                "immortality-postgres",
                "pg_isready",
                "-h",
                "127.0.0.1",
                "-U",
                "immortality",
                "-d",
                "immortality",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if pg_ready_check.returncode == 0:
            db_ready = True
            break
        time.sleep(1)

    if db_ready:
        immortalityPrint(
            "Docker container and PostgreSQL setup are ready", type="success"
        )
    else:
        raise CLIError(
            "PostgreSQL container started but is still not ready in container checks. "
            "Please check container logs first with "
            f"`{' '.join(compose_cmd)} -f {docker_compose_path} logs postgres`. "
            "If the issue persists, please set up PostgreSQL manually.",
            exit_code=1,
        )

    # 配置 immortality_checkpoints 数据库
    _setupCheckpointsDBIfNeeded()

    return {
        "db_user": "immortality",
        "db_password": "immortality_password",
        "db_host": "127.0.0.1",
        "db_port": "5432",
    }


def setupCLI(args: Namespace) -> int:
    """
    配置环境变量
    """

    def _resolveText(arg_value: str | None, label: str) -> str:
        if isinstance(arg_value, str):
            # 如果命令行参数有值，跳过交互输入直接返回
            return arg_value.strip()
        return input(f"{label}: ").strip()

    def _resolveSecret(arg_value: str | None, label: str) -> str:
        if isinstance(arg_value, str):
            # 如果命令行参数有值，跳过交互输入直接返回
            return arg_value.strip()
        return getpass.getpass(f"{label}: ").strip()

    cwd = Path.cwd()
    local_env_example_path = cwd / ".env.example"
    env_path = IMMORTALITY_ENV_PATH
    try:
        IMMORTALITY_HOME_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        raise CLIError(
            f"Cannot create config directory `{IMMORTALITY_HOME_DIR}`: {err}. Please create it manually.",
            exit_code=1,
        ) from err

    database_config_mode = questionary.select(
        "Choose database configuration mode",
        choices=[
            questionary.Choice(
                "Easy setup (Use cloud database with encrypted data)", value="easy"
            ),
            questionary.Choice(
                "Docker setup (recommended, but requires Docker installed)",
                value="docker",
            ),
            questionary.Choice("Manual setup", value="manual"),
        ],
    ).ask()
    if database_config_mode is None:
        raise CLIError("Setup cancelled by user.", exit_code=130)

    arg_db_user = getattr(args, "db_user", None)
    arg_db_password = getattr(args, "db_password", None)
    arg_db_host = getattr(args, "db_host", None)
    arg_db_port = getattr(args, "db_port", None)
    arg_ark_api_key = getattr(args, "ark_api_key", None)
    arg_doubao_2_0_lite = getattr(args, "doubao_2_0_lite", None)
    arg_doubao_2_0_mini = getattr(args, "doubao_2_0_mini", None)
    arg_embedding_endpoint_id = getattr(
        args, "embedding_model_endpoint_or_model_id", None
    )
    arg_lark_app_id = getattr(args, "lark_app_id", None)
    arg_lark_app_secret = getattr(args, "lark_app_secret", None)
    arg_lark_card_template_id = getattr(args, "lark_card_template_id", None)

    use_shared_database = database_config_mode == "easy"
    if database_config_mode == "docker":
        docker_db_values = dockerDBSteup()
        arg_db_user = arg_db_user or docker_db_values["db_user"]
        arg_db_password = arg_db_password or docker_db_values["db_password"]
        arg_db_host = arg_db_host or docker_db_values["db_host"]
        arg_db_port = arg_db_port or docker_db_values["db_port"]

    # easy 模式依赖远端服务，不采集本地数据库参数，但仍写入可解析的占位连接串。
    if use_shared_database:
        db_user = "unused"
        db_password = "unused"
        db_host = "shared-mode.invalid"
        db_port = "5432"
    else:
        db_user = _resolveText(arg_db_user, "db_user")
        db_password = _resolveSecret(arg_db_password, "db_password")
        db_host = _resolveText(arg_db_host, "db_host")
        db_port = _resolveText(arg_db_port, "db_port")

    login_secret = uuid.uuid4().hex
    ark_api_key = _resolveSecret(arg_ark_api_key, "ark_api_key")
    doubao_2_0_lite = _resolveText(
        arg_doubao_2_0_lite, "lite_model_endpoint_or_model_id"
    )
    doubao_2_0_mini = _resolveText(
        arg_doubao_2_0_mini, "mini_model_endpoint_or_model_id"
    )
    embedding_model_endpoint_or_model_id = _resolveText(
        arg_embedding_endpoint_id, "embedding_model_endpoint_or_model_id"
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
        "lite_model_endpoint_or_model_id": doubao_2_0_lite,
        "mini_model_endpoint_or_model_id": doubao_2_0_mini,
        "embedding_model_endpoint_or_model_id": embedding_model_endpoint_or_model_id,
        "lark_bot_app_id": lark_app_id,
        "lark_bot_app_secret": lark_app_secret,
        "lark_card_template_id": lark_card_template_id,
    }

    if local_env_example_path.exists():
        template = local_env_example_path.read_text(encoding="utf-8")
    else:
        try:
            template = (
                resources.files("src.cli")
                .joinpath("assets/.env.example")
                .read_text(encoding="utf-8")
            )
        except Exception as err:
            raise CLIError(
                f"Cannot load `.env.example` template from package: {err}", exit_code=1
            ) from err
    output = template
    for key, value in values.items():
        output = output.replace(f"<{key}>", value)
    output = re.sub(
        r"^USE_SHARED_DATABASE=.*$",
        f"USE_SHARED_DATABASE={'True' if use_shared_database else 'False'}",
        output,
        count=1,
        flags=re.MULTILINE,
    )

    try:
        env_path.write_text(output, encoding="utf-8")
    except OSError as err:
        raise CLIError(
            f"Cannot write env file `{env_path}`: {err}", exit_code=1
        ) from err

    # 共享数据库模式下依赖远程 API，不初始化本地数据库表。
    if not use_shared_database:
        initDatabaseIfNeeded()
    printServiceResInCLI(
        {
            "status": 200,
            "message": f"Environment variables are configured successfully, please run `immortality doctor` to check",
            "env_path": str(env_path),
        },
        as_json=args.json,
    )
    return 0


def logsCLI(args: Namespace) -> int:
    """
    动态打印当天日志
    """
    date = getattr(args, "date", None)
    if date:
        if not re.fullmatch(r"\d{8}", date):
            raise CLIError(
                "Invalid date format. Please use YYYYMMDD format.", exit_code=1
            )
        try:
            datetime.strptime(date, "%Y%m%d")
        except ValueError as err:
            raise CLIError(
                "Invalid date value. Please use a valid YYYYMMDD date.",
                exit_code=1,
            ) from err

    current_date = datetime.now().strftime("%Y%m%d")
    if not date:
        date = current_date

    log_path = IMMORTALITY_HOME_DIR / "logs" / f"app-{date}.log"
    if not log_path.exists():
        immortalityPrint(f"No logs for {date}", type="info")
        return 0
    try:
        check_logs = subprocess.run(
            ["tail", "-n", "100", "-f", str(log_path)],
            check=False,
            stderr=subprocess.PIPE,
            text=True,
        )
    except KeyboardInterrupt:
        return 0
    if check_logs.returncode != 0:
        raise CLIError(
            "Failed to tail logs: " + (check_logs.stderr or "").strip(),
            exit_code=1,
        )
    return 0
