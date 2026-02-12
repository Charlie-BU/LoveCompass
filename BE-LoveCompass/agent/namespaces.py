from typing import Optional, List, Dict, Any
from typing_extensions import Literal
from pydantic import BaseModel


class CompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChoiceDeltaToolCallFunction(BaseModel):
    name: Optional[str] = None
    arguments: Optional[str] = None


class ChoiceDeltaToolCall(BaseModel):
    index: int
    id: Optional[str] = None
    function: Optional[ChoiceDeltaToolCallFunction] = None
    type: Optional[str] = None


class ChoiceDelta(BaseModel):
    content: Optional[str] = None
    role: Optional[str] = None
    tool_calls: Optional[List[ChoiceDeltaToolCall]] = None
    reasoning_content: Optional[str] = None


class Choice(BaseModel):
    index: int
    delta: ChoiceDelta
    finish_reason: Optional[str] = None


class LLMResponse(BaseModel):
    error: Optional[str] = None


class LLMChunkResponse(LLMResponse, BaseModel):
    id: Optional[str] = None
    """A unique identifier for the chat completion. Each chunk has the same ID."""

    choices: List[Choice] = None
    """A list of chat completion choices.
    Can be more than one if `n` is greater than 1.
    """

    created: int = 0
    """The Unix timestamp (in seconds) of when the chat completion was created.

    Each chunk has the same timestamp.
    """

    model: Optional[str] = None
    """The model to generate the completion."""

    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    """The object type, which is always `chat.completion.chunk`."""

    usage: Optional[CompletionUsage] = None
    """
    An optional field that will only be present when you set
    `stream_options: {"include_usage": true}` in your request. When present, it
    contains a null value except for the last chunk which contains the token usage
    statistics for the entire request.
    """

    metadata: Optional[Dict[str, Any]] = None
