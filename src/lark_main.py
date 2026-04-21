import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    # 必须在load_dotenv()之后，否则会导致环境变量未加载
    from src.channels.lark.websocket_service import startLarkWebSocketServer
    from src.channels.lark.integration.index import messageHandler

    startLarkWebSocketServer(messageHandler)