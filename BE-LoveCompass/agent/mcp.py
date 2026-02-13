"""
通过ByteCloud AI PaaS注册MCP Server和MCP Tools
"""

import os
import logging
from bytedance.mcp_langgraph_adapter.bytedmcp_adapter import (
    convert_mcp_tools_to_langchain_tools,
)
from bytedance.mcp.mcp_client import byted_mcp_client_with_server_psm
from bytedance.mcp.custom_call_hooks import WithTraceEnabledHook
from bytedance.mcp.custom_http_hooks import ForwardLogIdHook
from .hooks import Hook

logger = logging.getLogger(__name__)


def get_mcp_psms_list():
    # your mcp psms, comma separated
    mcp_psms = os.getenv("BYTE_AIPAAS_MCP_PSM", "inf.sinf.sample_mcp")
    mcp_psms_list = mcp_psms.replace(" ", "").split(",")
    return mcp_psms_list


async def init_mcp_tools(mcp_psms_list: list[str]):
    try:
        # init the mcp server with the server psm
        mcp_client = await byted_mcp_client_with_server_psm(psm_list=mcp_psms_list)
        await mcp_client.connect_to_servers()

        # 作用：将当前的 logid 透传给 MCP 工具。
        # 如果不加这个，当工具调用出错时，无法通过全链路日志（Trace）将你的 Agent 请求和工具端的日志串联起来，排查问题会非常困难。
        await mcp_client.register_http_hooks(http_hooks=[ForwardLogIdHook()])

        await mcp_client.register_call_hooks_async(
            call_hooks=[Hook(), WithTraceEnabledHook()]
        )

        mcp_tools = convert_mcp_tools_to_langchain_tools(mcp_client)
        logger.info(f"load mcp tools: {mcp_tools}")
        return mcp_tools
    except Exception as e:
        logger.warning(
            f"Failed to initialize MCP tools: {e}, falling back to agent without tools"
        )
        return []
