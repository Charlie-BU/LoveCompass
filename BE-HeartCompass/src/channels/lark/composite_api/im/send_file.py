"""
发送文件消息，使用到两个OpenAPI：
1. [上传文件](https://open.feishu.cn/document/server-docs/im-v1/file/create)
2. [发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)
"""

import lark_oapi as lark
from lark_oapi.api.im.v1 import *

from typing import TypedDict


class SendFileRequest(TypedDict):
    file_type: str | None  # 文件类型，必填
    file_name: str | None  # 带后缀的文件名，必填
    file: IO[Any] | None  # 文件内容，必填
    duration: int | None  # 文件的时长(ms)，选填
    receive_id_type: str | None  # 消息接收者ID类型，必填
    receive_id: str | None  # 消息接收者的ID，必填
    uuid: str | None  # 消息uuid，选填


class SendFileResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__()
        self.create_file_response: Optional[CreateFileResponseBody] = None
        self.create_message_response: Optional[CreateMessageResponseBody] = None


# 发送文件消息
def sendFile(client: lark.Client, request: SendFileRequest) -> BaseResponse:
    # 上传文件
    create_file_req = (
        CreateFileRequest.builder()
        .request_body(
            CreateFileRequestBody.builder()
            .file_type(request.get("file_type"))
            .file_name(request.get("file_name"))
            .duration(request.get("duration"))
            .file(request.get("file"))
            .build()
        )
        .build()
    )

    create_file_resp = client.im.v1.file.create(create_file_req)

    if not create_file_resp.success():
        lark.logger.error(
            f"client.im.v1.file.create failed, "
            f"code: {create_file_resp.code}, "
            f"msg: {create_file_resp.msg}, "
            f"log_id: {create_file_resp.get_log_id()}"
        )
        return create_file_resp

    # 发送消息
    option = (
        lark.RequestOption.builder()
        .headers({"X-Tt-Logid": create_file_resp.get_log_id()})
        .build()
    )
    create_message_req = (
        CreateMessageRequest.builder()
        .receive_id_type(request.get("receive_id_type"))
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(request.get("receive_id"))
            .msg_type("file")
            .content(lark.JSON.marshal(create_file_resp.data))
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
        return create_message_resp

    # 返回结果
    response = SendFileResponse()
    response.code = 0
    response.msg = "success"
    response.create_file_response = create_file_resp.data
    response.create_message_response = create_message_resp.data

    return response
