"""
发送卡片消息，使用到 OpenAPI：
1. [发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)
"""

import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from typing import Any, Optional, TypedDict


class SendCardRequest(TypedDict):
    receive_id_type: str | None
    receive_id: str | None
    card_template_id: str | None
    card_variables: dict[str, Any] | None = None


class SendCardResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__()
        self.create_message_response: Optional[CreateMessageResponseBody] = None


def sendCard(client: lark.Client, request: SendCardRequest) -> SendCardResponse:
    card_variables = request.get("card_variables")
    if (
        not card_variables
        or not card_variables.get("title")
        or not card_variables.get("content")
    ):
        raise ValueError("Title and content are required")
    theme = card_variables.get("theme")
    if (
        theme
        and theme != ""
        and theme
        not in (
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
        )
    ):
        raise ValueError("Theme is invalid")
    if not theme:
        card_variables["theme"] = "blue"

    content = json.dumps(
        {
            "type": "template",
            "data": {
                "template_id": request.get("card_template_id"),
                "template_variable": card_variables or {},
            },
        },
        ensure_ascii=False,
    )

    create_message_req = (
        CreateMessageRequest.builder()
        .receive_id_type(request.get("receive_id_type"))
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(request.get("receive_id"))
            .msg_type("interactive")
            .content(content)
            .build()
        )
        .build()
    )

    create_message_resp: CreateMessageResponse = client.im.v1.message.create(
        create_message_req
    )

    if not create_message_resp.success():
        lark.logger.error(
            f"client.im.v1.message.create failed, "
            f"code: {create_message_resp.code}, "
            f"msg: {create_message_resp.msg}, "
            f"log_id: {create_message_resp.get_log_id()}"
        )
        response = SendCardResponse()
        response.code = create_message_resp.code
        response.msg = create_message_resp.msg
        response.create_message_response = create_message_resp.data
        return response

    response = SendCardResponse()
    response.code = 0
    response.msg = "success"
    response.create_message_response = create_message_resp.data

    return response
