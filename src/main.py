import logging
from datetime import datetime
from dotenv import load_dotenv


def preconfig() -> None:
    """
    预配置
    """
    # 加载环境变量
    from src.cli.constants import IMMORTALITY_ENV_PATH, IMMORTALITY_HOME_DIR

    load_dotenv(IMMORTALITY_ENV_PATH)
    # 配置日志
    LOG_DIR = IMMORTALITY_HOME_DIR / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / f"app-{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
        force=True,
    )


preconfig()


def main() -> None:
    """
    入口
    """
    from src.channels.lark.websocket import startLarkService

    startLarkService()


if __name__ == "__main__":
    main()
