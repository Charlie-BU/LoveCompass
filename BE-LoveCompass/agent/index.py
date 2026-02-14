from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from typing import List
from robyn import Request, StreamingResponse
import logging


from .adapter import (
    convert_req_to_messages,
    from_astream_model_message,
    process_response_message,
    end_stop_message,
    from_error_message,
    from_ainvoke_model_messages,
)

logger = logging.getLogger(__name__)


def create_agent_graph(
    llm: ChatOpenAI, tools: List[BaseTool], system_prompt: str
) -> CompiledStateGraph:
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )


async def wrap_chat(ReAct_agent):
    async def chat(request: Request):
        body = request.json()
        is_stream = body.get("stream", True)

        async def event_generator():
            try:
                callbacks = []
                input_message = convert_req_to_messages(body)
                if is_stream:
                    async for resp in ReAct_agent.astream(
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
                    resp = await ReAct_agent.ainvoke(
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
