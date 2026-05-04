import logging
import os
from typing import Literal

from src.channels.lark.client import larkClient
from src.channels.lark.composite_api.im.send_card import sendCard
from src.channels.lark.composite_api.im.send_text import SendTextRequest, sendText


_lark_client = larkClient()
logger = logging.getLogger(__name__)


def sendText2OpenId(open_id: str, text: str) -> None:
    """
    发送文本消息到飞书 openid
    """
    response = sendText(
        _lark_client,
        SendTextRequest(
            text=text,
            receive_id_type="open_id",
            receive_id=open_id,
        ),
    )
    if getattr(response, "code", None) != 0:
        logger.warning(
            f"Fail to send text to open_id: {open_id}, code: {response.code}, msg: {response.msg}"
        )


def sendCard2OpenId(
    open_id: str,
    title: str,
    content: str,
    theme: (
        Literal[
            "blue",
            "wathet",
            "turquoise",
            "green",
            "yellow",
            "orange",
            "red",
            "carmine",
            "violet",
            "purple",
            "indigo",
            "grey",
            "default",
        ]
        | None
    ) = None,
) -> None:
    """
    发送飞书卡片到飞书 openid
    """
    LARK_CARD_TEMPLATE_ID = os.getenv("LARK_CARD_TEMPLATE_ID")
    if not LARK_CARD_TEMPLATE_ID:
        logger.warning("LARK_CARD_TEMPLATE_ID is not set")
        # 降级到 sendText2OpenId
        sendText2OpenId(open_id, f"『Immortality』{title}\n{content}")
        return

    response = sendCard(
        _lark_client,
        {
            "receive_id_type": "open_id",
            "receive_id": open_id,
            "card_template_id": LARK_CARD_TEMPLATE_ID,
            "card_variables": {
                "title": title,
                "content": content,
                "theme": theme or "blue",
            },
        },
    )
    if getattr(response, "code", None) != 0:
        logger.warning(
            f"Fail to send card to open_id: {open_id}, code: {response.code}, msg: {response.msg}"
        )
        # 降级到 sendText2OpenId
        sendText2OpenId(open_id, f"『Immortality』{title}\n{content}")
        return
