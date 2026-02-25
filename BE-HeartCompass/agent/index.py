from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from typing import List, Optional
from robyn import Request, StreamingResponse
from dotenv import load_dotenv
import logging
import os
import asyncio


from .ark import arkClient
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
_ark_client = arkClient()
_agent_instance: Optional[CompiledStateGraph] = None
_agent_lock = asyncio.Lock()


async def getAgent():
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance
    # 双检查锁模式，确保线程安全
    async with _agent_lock:
        if _agent_instance is not None:
            return _agent_instance
        system_prompt = await getPrompt(os.getenv("SYSTEM_PROMPT"))
        llm: ChatOpenAI = prepareLLM()
        agent_instance = create_agent(model=llm, tools=[], system_prompt=system_prompt)
        _agent_instance = agent_instance
        return agent_instance


# 处理chat_completions请求
async def wrapChat(ReActAgent: CompiledStateGraph):
    async def chat(request: Request):
        body = request.json()
        is_stream = body.get("stream", True)

        async def eventGenerator():
            try:
                callbacks = []
                input_message = convertReqToMessages(body)
                if is_stream:
                    async for resp in ReActAgent.astream(
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
                    resp = await ReActAgent.ainvoke(
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


# 无上下文直接调用agent
async def askWithNoContext(prompt: str, ReActAgent: CompiledStateGraph) -> str:
    messages = [HumanMessage(content=prompt)]
    resp = await ReActAgent.ainvoke({"messages": messages})
    if resp and "messages" in resp and len(resp["messages"]) > 0:
        return resp["messages"][-1].content
    return ""


# 注意⚠️：多模态向量化能力模型不支持 OpenAI API，使用Ark SDK调用
# 向量化文本
async def vectorizeText(text: str) -> list[float]:
    resp = await _ark_client.multimodal_embeddings.create(
        model=os.getenv("EMBEDDING_ENDPOINT_ID", ""),
        input=[
            {"type": "text", "text": text},
        ],
        dimensions=1024,
    )
    return resp.data.embedding


# 向量化图片
async def vectorizeImage(image_url: str) -> list[float]:
    resp = await _ark_client.multimodal_embeddings.create(
        model=os.getenv("EMBEDDING_ENDPOINT_ID", ""),
        input=[
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            },
        ],
        dimensions=1024,
    )
    return resp.data.embedding


# 向量化混合输入
async def vectorizeMixed(text: List[str], image_url: List[str]) -> list[float]:
    input_list = [{"type": "text", "text": t} for t in text] + [
        {"type": "image_url", "image_url": {"url": u}} for u in image_url
    ]
    resp = await _ark_client.multimodal_embeddings.create(
        model=os.getenv("EMBEDDING_ENDPOINT_ID", ""),
        input=input_list,
        dimensions=1024,
    )
    return resp.data.embedding
