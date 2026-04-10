from typing import Optional, List, Dict, Any
import time
import uuid
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessage,
)

from src.agents.types import (
    LLMChunkResponse,
    ChoiceDelta,
    Choice,
    ChoiceDeltaToolCallFunction,
    ChoiceDeltaToolCall,
)


def convertReqToMessages(req: dict) -> list:
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


def fromAIMessage(msg: AIMessage, debug: bool = False) -> LLMChunkResponse:
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


def fromToolMessage(message: ToolMessage, debug: bool = False) -> LLMChunkResponse:
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


def endStopMessage() -> LLMChunkResponse:
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


def fromErrorMessage(err: str) -> LLMChunkResponse:
    delta = ChoiceDelta(content=f"ERROR: {err}", role="assistant")
    choice = Choice(index=0, delta=delta, finish_reason="stop")
    return LLMChunkResponse(
        id="",
        choices=[choice],
        created=int(time.time()),
        object="chat.completion.chunk",
        metadata=None,
    )


def fromAstreamModelMessage(
    invoke: tuple, debug: bool = False
) -> Optional[LLMChunkResponse]:
    """Convert Chunk an LLMChunkResponse."""
    message = invoke[0]
    try:
        if isinstance(message, AIMessage):
            return fromAIMessage(message, debug)
        elif isinstance(message, ToolMessage):
            return fromToolMessage(message, debug)
        elif isinstance(message, HumanMessage):
            return None
    except Exception as e:
        raise Exception(f"Error processing message: {message}. Error: {str(e)}")

    raise ValueError(f"Unsupported message type: {type(message)}")


def processResponseMessage(msg: LLMChunkResponse):
    if not (
        msg.choices[0].delta.content
        or msg.choices[0].delta.reasoning_content
        or msg.choices[0].finish_reason
    ):
        if (not msg.usage) or (msg.usage.total_tokens == 0):
            return None
    return f"data:{msg.model_dump_json(exclude_unset=True, exclude_none=True)}\r\n\r\n"


def fromAinvokeModelMessages(messages, debug: bool = False) -> list[LLMChunkResponse]:
    """Convert a list of messages to a list of LLMChunkResponse."""
    res = []
    for message in messages:
        if isinstance(message, AIMessage):
            res.append(fromAIMessage(message, debug))
        elif isinstance(message, ToolMessage):
            res.append(fromToolMessage(message, debug))
    return res


# 适配 Ark SDK
def langchain2OpenAIChatMessages(
    messages: List[BaseMessage], is_ark_responses_messages: bool = False
) -> List[Dict[str, Any]]:
    """
    【重要‼️】将 LangChain messages 转换为 Ark Responses API 格式
    """

    def _roleMap(message: BaseMessage) -> str:
        if isinstance(message, HumanMessage):
            return "user"
        elif isinstance(message, AIMessage):
            return "assistant"
        elif isinstance(message, SystemMessage):
            return "system"
        else:
            raise ValueError(f"Unsupported message type: {type(message)}")

    # 将不同格式统一为 Ark Responses API 格式
    def _normalizeBlock(
        block: Dict[str, Any], is_ark_responses_messages: bool
    ) -> Dict[str, Any]:
        block_type = block.get("type")
        # 文本统一
        if block_type in ("text", "input_text"):
            if is_ark_responses_messages:
                return {"type": "input_text", "text": block.get("text", "")}
            return {"type": "text", "text": block.get("text", "")}
        # 图片统一
        elif block_type in ("image_url", "input_image"):
            if is_ark_responses_messages:
                return {
                    "type": "input_image",
                    "image_url": block.get("image_url") or block.get("url"),
                }
            return {
                "type": "image_url",
                "image_url": block.get("image_url") or block.get("url", ""),
            }
        # 视频统一
        elif block_type in ("video_url", "input_video"):
            if is_ark_responses_messages:
                return {
                    "type": "input_video",
                    "video_url": block.get("video_url") or block.get("url"),
                }
            return {
                "type": "video_url",
                "video_url": block.get("video_url") or block.get("url", ""),
            }
        # 文档统一
        elif block_type in ("file_url", "input_file"):
            if is_ark_responses_messages:
                return {
                    "type": "input_file",
                    "file_url": block.get("file_url") or block.get("url"),
                }
            return {
                "type": "file_url",
                "file_url": block.get("file_url") or block.get("url", ""),
            }
        # 未知类型直接报错
        raise ValueError(f"Unsupported content block type: {block_type}")

    def _contentMap(
        content: Any, role: str, is_ark_responses_messages: bool
    ) -> List[Dict[str, Any]] | str:
        # system / assistant 为纯文本
        if role in ("system", "assistant"):
            return content

        # 字符串 → text block
        if isinstance(content, str):
            if is_ark_responses_messages:
                return [{"type": "input_text", "text": content}]
            return content

        # list → 多模态
        if isinstance(content, list):
            return [
                _normalizeBlock(item, is_ark_responses_messages) for item in content
            ]

        raise ValueError(f"Unsupported content type: {type(content)}")

    result = []

    for msg in messages:
        role = _roleMap(msg)
        result.append(
            {
                "role": role,
                "content": _contentMap(msg.content, role, is_ark_responses_messages),
            }
        )

    return result
