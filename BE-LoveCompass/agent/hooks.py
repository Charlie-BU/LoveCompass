import logging

from typing import Any

from bytedance.mcp import (
    HttpRequest,
    CallHook,
    CallToolResult,
)

logger = logging.getLogger(__name__)


class Hook(CallHook):
    def before_call(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None,
        **kwargs,
    ):
        logger.info(
            f"before_call hook, server_name={server_name}, tool_name={tool_name}, arguments={arguments}, kwargs={kwargs}"
        )

    def after_call(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None,
        result: CallToolResult,
        **kwargs,
    ):
        logger.info(
            f"after_call hook, server_name={server_name}, tool_name={tool_name}, arguments={arguments}, result={result}, kwargs={kwargs}"
        )

    def on_http_call(
        self, server_name: str, tool_name: str, request: HttpRequest, **kwargs
    ):
        logger.info(
            f"on_http_call hook, server_name={server_name}, tool_name={tool_name}, request={request}, kwargs={kwargs}"
        )
