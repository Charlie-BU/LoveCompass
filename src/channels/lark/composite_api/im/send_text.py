"""
发送文本消息，使用到 OpenAPI：
1. [发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)
"""

import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from typing import Optional, TypedDict


class SendTextRequest(TypedDict):
    text: str | None = None
    receive_id_type: str | None = None
    receive_id: str | None = None
    uuid: str | None = None


class SendTextResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__()
        self.create_message_response: Optional[CreateMessageResponseBody] = None


def sendText(client: lark.Client, request: SendTextRequest) -> SendTextResponse:
    create_message_req = (
        CreateMessageRequest.builder()
        .receive_id_type(request.get("receive_id_type"))
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(request.get("receive_id"))
            .msg_type("text")
            .content(lark.JSON.marshal({"text": request.get("text")}))
            .uuid(request.get("uuid"))
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
        response = SendTextResponse()
        response.code = create_message_resp.code
        response.msg = create_message_resp.msg
        response.create_message_response = create_message_resp.data
        return response

    response = SendTextResponse()
    response.code = 0
    response.msg = "success"
    response.create_message_response = create_message_resp.data

    return response
