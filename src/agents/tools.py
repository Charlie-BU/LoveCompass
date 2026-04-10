"""
todo
"""

import json
import logging
from typing import Annotated, Callable, List
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph.state import Runnable

# from src.database.index import session
# from src.database.models import 

logger = logging.getLogger(__name__)



class ToolAndItsArgsHandler:
    def __init__(self, tool: BaseTool, args_handler: Callable | None = None):
        self.tool = tool
        self.args_handler = args_handler  # 手动处理tool call参数的方法。接受两个参数：tool_call和messages。返回处理后的参数dict。

    def process_args(self, tool_call: dict, messages: list) -> dict:
        # llm 给出的tool call参数
        tool_args = tool_call.get("args") or {}
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except json.JSONDecodeError:
                tool_args = {}
        if not isinstance(tool_args, dict):
            tool_args = {}
        if self.args_handler:
            handled_args = self.args_handler(tool_call, messages)
            if isinstance(handled_args, dict):
                tool_args = handled_args
            else:
                logger.error(
                    f"Args handler {self.args_handler.__name__} return non-dict value {handled_args}"
                )
        return tool_args


async def handleIfToolCall(
    tools_and_args_handlers: List[ToolAndItsArgsHandler],
    messages: list,
    llm_with_tools: Runnable[LanguageModelInput, AIMessage],
    llm_response: AIMessage,
    max_tool_round: int = 3,
) -> tuple[AIMessage, list]:
    # 为降低时间复杂度，提前构建tool_name到ToolAndItsArgsHandler的映射
    tool_map = {ta.tool.name: ta for ta in tools_and_args_handlers}
    tool_round = 0

    while (
        getattr(llm_response, "tool_calls", None)
        and isinstance(llm_response.tool_calls, list)
        and len(llm_response.tool_calls) > 0
        and tool_round < max(0, max_tool_round)
    ):
        # 把新一轮的llm_response加入messages
        messages.append(llm_response)

        for tool_call in llm_response.tool_calls:
            tool_name = tool_call.get("name")
            tool_call_id = tool_call.get("id")
            if not tool_call_id:
                logger.error(f"Tool call id not found in {tool_call}")
                continue

            # find tool
            tool_and_args_handler = tool_map.get(tool_name)
            if tool_and_args_handler is None:
                logger.error(f"Tool {tool_name} not found")
                messages.append(
                    ToolMessage(
                        content=f"ERROR: tool {tool_name} not found\nThis message should be ignored.",
                        tool_call_id=tool_call_id,
                    )
                )
                continue

            # call tool
            tool = tool_and_args_handler.tool
            tool_args = tool_and_args_handler.process_args(tool_call, messages)

            tool_result = None
            try:
                tool_result = await tool.ainvoke(tool_args)
            except Exception as e:
                logger.error(f"Tool {tool_name} error: {e}")
                tool_result = f"ERROR: {e}\nThis message should be ignored."

            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call_id,
                )
            )

        llm_response = await llm_with_tools.ainvoke(messages)
        tool_round += 1

    return llm_response, messages


# @tool
# def useKnowledge(relation_chain_id: Annotated[int, "Relation chain id"]) -> str:
#     """Get MBTI/personality knowledge for this relation_chain to enrich persona and relationship context."""
#     logger.info(f"useKnowledge Tool called with relation_chain_id: {relation_chain_id}")
#     with session() as db:
#         relation_chain = db.get(RelationChain, relation_chain_id)
#         if relation_chain is None:
#             logger.error(f"Relation chain {relation_chain_id} not found")
#             return ""
#         return relation_chain.relevant_knowledge