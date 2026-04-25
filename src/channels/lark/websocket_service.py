import json
import logging
import os
from typing import Callable
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
)

logger = logging.getLogger(__name__)


def _extractText(content: str) -> str:
    if not content:
        return ""
    try:
        payload = json.loads(content)
        if isinstance(payload, dict):
            text = payload.get("text")
            if isinstance(text, str):
                return text
    except Exception:
        return content
    return ""


def messageAdapter(
    data: P2ImMessageReceiveV1, message_handler: Callable[[str, str], None]
) -> None:
    message = data.event.message
    if message.message_type == "text":
        text = _extractText(message.content)
        try:
            message_handler(message=text, open_id=data.event.sender.sender_id.open_id)
        except Exception as e:
            logger.error(f"failed to handle text message, err: {e}", exc_info=True)
        return
    if message.message_type == "image":
        # 暂弃用
        return
    if message.message_type == "file":
        # 暂弃用
        return
    logger.info(f"ignore unsupported message type: {message.message_type}")


def startLarkWebSocketServer(message_handler: Callable[[str, str], None]) -> None:
    """
    启动 Lark WebSocket 服务器
    """
    app_id = os.getenv("LARK_APP_ID", "")
    app_secret = os.getenv("LARK_APP_SECRET", "")

    if not app_id or not app_secret:
        return

    event_handler = (
        lark.EventDispatcherHandler.builder("", "", lark.LogLevel.INFO)
        .register_p2_im_message_receive_v1(
            lambda data: messageAdapter(data, message_handler)
        )
        .build()
    )
    ws_client = lark.ws.Client(
        app_id,
        app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO,
    )
    ws_client.start()


def startLarkService():
    """
    启动 Lark 服务
    """
    # 延迟导入，避免环境变量未加载
    from src.channels.lark.integration.index import messageHandler
    from src.database.models import initDatabaseIfNeeded

    initDatabaseIfNeeded()
    startLarkWebSocketServer(messageHandler)
