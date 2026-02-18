from typing import Optional
import time
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
import uuid

from .namespaces import (
    LLMChunkResponse,
    ChoiceDelta,
    Choice,
    ChoiceDeltaToolCallFunction,
    ChoiceDeltaToolCall,
)


def convert_req_to_messages(req: dict) -> list:
    new_messages = []
    for msg in req["messages"]:
        if "role" in msg:
            role = msg["role"]
        else:
            role = "user"
        content = msg["content"]
        if role == "user":
            new_messages.append(HumanMessage(content=content))
        elif role == "system":
            new_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            new_messages.append(AIMessage(content=content))
        elif role == "tool":
            tool_call_id = msg.get("id")
            if not tool_call_id:
                tool_call_id = f"call_{uuid.uuid4().hex[:24]}"
            new_messages.append(
                ToolMessage(content=content, tool_call_id=str(tool_call_id))
            )
        else:
            new_messages.append(HumanMessage(content=content))
    return new_messages


def from_ai_message(msg: AIMessage, debug: bool = False) -> LLMChunkResponse:
    response_meta = msg.response_metadata or {}
    finish_reason = response_meta.get("finish_reason", None)
    content = msg.content
    delta = ChoiceDelta(content=content, role="assistant")
    choice = Choice(index=0, delta=delta, finish_reason=finish_reason)
    return LLMChunkResponse(
        id=str(msg.id) if msg.id else None,
        choices=[choice],
        created=int(time.time()),
        object="chat.completion.chunk",
        metadata=None,
    )


def from_tool_message(message: ToolMessage, debug: bool = False) -> LLMChunkResponse:
    content = message.content
    tool_call_function = ChoiceDeltaToolCallFunction(
        name=message.name,
    )
    tool_call = ChoiceDeltaToolCall(
        index=0, id=message.tool_call_id, function=tool_call_function, type="function"
    )
    delta = ChoiceDelta(content=content, role="tool", tool_calls=[tool_call])
    choice = Choice(index=0, delta=delta, finish_reason="tool_calls")
    return LLMChunkResponse(
        id=str(message.id) if message.id else None,
        choices=[choice],
        created=int(time.time()),
        object="chat.completion.chunk",
        metadata=None,
    )


def end_stop_message() -> LLMChunkResponse:
    delta = ChoiceDelta(content="", role="assistant")
    choice = Choice(index=0, delta=delta, finish_reason="stop")
    return LLMChunkResponse(
        id="",
        choices=[choice],
        created=int(time.time()),
        object="chat.completion.chunk",
        usage=None,
        metadata=None,
    )


def from_error_message(err: str) -> LLMChunkResponse:
    delta = ChoiceDelta(content=f"ERROR: {err}", role="assistant")
    choice = Choice(index=0, delta=delta, finish_reason="stop")
    return LLMChunkResponse(
        id="",
        choices=[choice],
        created=int(time.time()),
        object="chat.completion.chunk",
        metadata=None,
    )


def from_astream_model_message(
    invoke: tuple, debug: bool = False
) -> Optional[LLMChunkResponse]:
    """Convert Chunk an LLMChunkResponse."""
    message = invoke[0]
    try:
        if isinstance(message, AIMessage):
            return from_ai_message(message, debug)
        elif isinstance(message, ToolMessage):
            return from_tool_message(message, debug)
        elif isinstance(message, HumanMessage):
            return None
    except Exception as e:
        raise Exception(f"Error processing message: {message}. Error: {str(e)}")

    raise ValueError(f"Unsupported message type: {type(message)}")


def process_response_message(msg: LLMChunkResponse):
    if not (
        msg.choices[0].delta.content
        or msg.choices[0].delta.reasoning_content
        or msg.choices[0].finish_reason
    ):
        if (not msg.usage) or (msg.usage.total_tokens == 0):
            return None
    return f"data:{msg.model_dump_json(exclude_unset=True, exclude_none=True)}\r\n\r\n"


def from_ainvoke_model_messages(
    messages, debug: bool = False
) -> list[LLMChunkResponse]:
    """Convert a list of messages to a list of LLMChunkResponse."""
    res = []
    for message in messages:
        if isinstance(message, AIMessage):
            res.append(from_ai_message(message, debug))
        elif isinstance(message, ToolMessage):
            res.append(from_tool_message(message, debug))
    return res
