from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from typing import List, Optional
from robyn import Request, StreamingResponse
from dotenv import load_dotenv
import logging
import os
import asyncio

from .llm import prepareLLM
from .prompt import getPrompt

# from .mcp import get_mcp_psms_list, init_mcp_tools
from .adapter import (
    convertReqToMessages,
    fromAstreamModelMessage,
    processResponseMessage,
    endStopMessage,
    fromErrorMessage,
    fromAinvokeModelMessages,
)

load_dotenv()
logger = logging.getLogger(__name__)


# 全局单例
_agent_instance: Optional[CompiledStateGraph] = None
_agent_lock = asyncio.Lock()


# 暂弃用
async def getAgent() -> CompiledStateGraph:
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance
    # 双检查锁模式，确保线程安全
    async with _agent_lock:
        if _agent_instance is not None:
            return _agent_instance
        system_prompt = await getPrompt(os.getenv("SYSTEM_PROMPT"))
        llm: ChatOpenAI = prepareLLM(model="DOUBAO_2_0_LITE", options={
            "temperature": 0.5,
            "reasoning_effort": "low",
        })
        agent_instance = create_agent(model=llm, tools=[], system_prompt=system_prompt)
        _agent_instance = agent_instance
        return agent_instance


# 处理chat_completions请求
async def wrapChat(react_agent: CompiledStateGraph):
    async def chat(request: Request):
        body = request.json()
        is_stream = body.get("stream", True)

        async def eventGenerator():
            try:
                callbacks = []
                input_message = convertReqToMessages(body)
                if is_stream:
                    async for resp in react_agent.astream(
                        {"messages": input_message},
                        stream_mode="messages",
                        config=RunnableConfig(callbacks=callbacks),
                    ):
                        resp_msg = fromAstreamModelMessage(resp, False)
                        # to adapter the ark ui
                        if not resp_msg:
                            continue

                        if isinstance(resp_msg, list):
                            for item in resp_msg:
                                result = processResponseMessage(item)
                                if result:
                                    yield result
                        else:
                            result = processResponseMessage(resp_msg)
                            if result:
                                yield result
                else:
                    resp = await react_agent.ainvoke(
                        {"messages": input_message},
                        config=RunnableConfig(callbacks=callbacks),
                    )
                    resp_msg = fromAinvokeModelMessages(resp.get("messages", []), False)
                    if resp_msg:
                        for item in resp_msg:
                            result = processResponseMessage(item)
                            if result:
                                yield result
                # [DONE] means end.
                logger.info("-----------chat done--------")
                yield f"data:{endStopMessage().model_dump_json(exclude_unset=True, exclude_none=True)}\r\n\r\n"
                yield "data:[DONE]\r\n\r\n"

            except Exception as e:
                logger.error(f"failed to chat, {e}", exc_info=True)
                yield processResponseMessage(fromErrorMessage(str(e)))
                yield f"data:{endStopMessage().model_dump_json(exclude_unset=True, exclude_none=True)}\r\n\r\n"
                yield "data:[DONE]\r\n\r\n"

        # Wrap the async generator in a StreamingResponse to properly stream the response
        return StreamingResponse(
            eventGenerator(),
            media_type="text/event-stream",
        )

    return chat
