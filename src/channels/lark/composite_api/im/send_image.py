"""
发送图片消息，使用到两个OpenAPI：
1. [上传图片](https://open.feishu.cn/document/server-docs/im-v1/image/create)
2. [发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)
"""

import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from typing import Any, IO, Optional, TypedDict


class SendImageRequest(TypedDict):
    image: IO[Any] | None = None  # 图片，必填
    receive_id_type: str | None = None  # 消息接收者ID类型，必填
    receive_id: str | None = None  # 消息接收者的ID，必填
    uuid: str | None = None  # 消息uuid，选填


class SendImageResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__()
        self.create_image_response: Optional[CreateImageResponseBody] = None
        self.create_message_response: Optional[CreateMessageResponseBody] = None


# 发送图片消息
def sendImage(client: lark.Client, request: SendImageRequest) -> SendImageResponse:
    # 上传图片
    create_image_req = (
        CreateImageRequest.builder()
        .request_body(
            CreateImageRequestBody.builder()
            .image_type("message")
            .image(request.get("image"))
            .build()
        )
        .build()
    )

    create_image_resp = client.im.v1.image.create(create_image_req)

    if not create_image_resp.success():
        lark.logger.error(
            f"client.im.v1.image.create failed, "
            f"code: {create_image_resp.code}, "
            f"msg: {create_image_resp.msg}, "
            f"log_id: {create_image_resp.get_log_id()}"
        )
        response = SendImageResponse()
        response.code = create_image_resp.code
        response.msg = create_image_resp.msg
        response.create_image_response = create_image_resp.data
        return response

    # 发送消息
    option = (
        lark.RequestOption.builder()
        .headers({"X-Tt-Logid": create_image_resp.get_log_id()})
        .build()
    )
    create_message_req = (
        CreateMessageRequest.builder()
        .receive_id_type(request.get("receive_id_type"))
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(request.get("receive_id"))
            .msg_type("image")
            .content(lark.JSON.marshal(create_image_resp.data))
            .uuid(request.get("uuid"))
            .build()
        )
        .build()
    )

    create_message_resp: CreateMessageResponse = client.im.v1.message.create(
        create_message_req, option
    )

    if not create_message_resp.success():
        lark.logger.error(
            f"client.im.v1.message.create failed, "
            f"code: {create_message_resp.code}, "
            f"msg: {create_message_resp.msg}, "
            f"log_id: {create_message_resp.get_log_id()}"
        )
        response = SendImageResponse()
        response.code = create_message_resp.code
        response.msg = create_message_resp.msg
        response.create_image_response = create_image_resp.data
        response.create_message_response = create_message_resp.data
        return response

    # 返回结果
    response = SendImageResponse()
    response.code = 0
    response.msg = "success"
    response.create_image_response = create_image_resp.data
    response.create_message_response = create_message_resp.data

    return response
