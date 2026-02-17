from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from typing import List
from robyn import Request, StreamingResponse
import logging

from .llm import prepare_llm

# from .mcp import get_mcp_psms_list, init_mcp_tools
from .adapter import (
    convert_req_to_messages,
    from_astream_model_message,
    process_response_message,
    end_stop_message,
    from_error_message,
    from_ainvoke_model_messages,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = ""
# SYSTEM_PROMPT = """
# 你是“LoveCompass”恋爱辅助产品的智能助手。
# 你的目标是基于用户提供的上下文，帮助用户理解关系现状、构建对方画像、给出更合适的沟通与推进建议。
# 你必须使用中文回答。

# # 核心原则：
# 1. 100%利用用户提供的上下文为准，不编造事实。
# 2. 用MBTI作为参考，不把MBTI当作决定性结论。
# 3. 建议需要可执行、低风险、尊重对方边界与感受。
# 4. 先理解再建议，明确问题与目标后输出方案。
# 5. 当上下文不足时，提出高价值的补充信息请求。
# """

# 全局单例
_agent_instance: CompiledStateGraph = None


def get_agent():
    global _agent_instance
    if _agent_instance is None:
        # 1. Prepare LLM
        llm = prepare_llm()

        # 2. Prepare Tools
        # mcp_psms_list = get_mcp_psms_list()
        # tools = await init_mcp_tools(mcp_psms_list)

        # 3. Init Agent
        _agent_instance = create_agent_graph(
            llm=llm, tools=[], system_prompt=SYSTEM_PROMPT
        )

    return _agent_instance


def create_agent_graph(
    llm: ChatOpenAI, tools: List[BaseTool], system_prompt: str
) -> CompiledStateGraph:
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )


async def wrap_chat(ReActAgent: CompiledStateGraph):
    async def chat(request: Request):
        body = request.json()
        is_stream = body.get("stream", True)

        async def event_generator():
            try:
                callbacks = []
                input_message = convert_req_to_messages(body)
                if is_stream:
                    async for resp in ReActAgent.astream(
                        {"messages": input_message},
                        stream_mode="messages",
                        config=RunnableConfig(callbacks=callbacks),
                    ):
                        resp_msg = from_astream_model_message(resp, False)
                        # to adapter the ark ui
                        if not resp_msg:
                            continue

                        if isinstance(resp_msg, list):
                            for item in resp_msg:
                                result = process_response_message(item)
                                if result:
                                    yield result
                        else:
                            result = process_response_message(resp_msg)
                            if result:
                                yield result
                else:
                    resp = await ReActAgent.ainvoke(
                        {"messages": input_message},
                        config=RunnableConfig(callbacks=callbacks),
                    )
                    resp_msg = from_ainvoke_model_messages(
                        resp.get("messages", []), False
                    )
                    if resp_msg:
                        for item in resp_msg:
                            result = process_response_message(item)
                            if result:
                                yield result
                # [DONE] means end.
                logger.info("-----------chat done--------")
                yield f"data:{end_stop_message().model_dump_json(exclude_unset=True, exclude_none=True)}\r\n\r\n"
                yield "data:[DONE]\r\n\r\n"

            except Exception as e:
                logger.error(f"failed to chat, {e}", exc_info=True)
                yield process_response_message(from_error_message(str(e)))
                yield f"data:{end_stop_message().model_dump_json(exclude_unset=True, exclude_none=True)}\r\n\r\n"
                yield "data:[DONE]\r\n\r\n"

        # Wrap the async generator in a StreamingResponse to properly stream the response
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    return chat
