import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    # 延迟导入，避免环境变量未加载
    from src.channels.lark.websocket_service import startLarkWebSocketServer
    from src.channels.lark.integration.index import messageHandler
    from src.database.models import initDatabaseIfNeeded

    initDatabaseIfNeeded()
    startLarkWebSocketServer(messageHandler)
