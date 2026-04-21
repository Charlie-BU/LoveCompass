import logging
import os
from typing import Literal, List, Mapping, TypedDict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, HumanMessage

from src.agents.ark import arkClient
from src.agents.adapter import langchain2OpenAIChatMessages

logger = logging.getLogger(__name__)


class LLMOptions(TypedDict, total=False):
    temperature: float | None
    max_tokens: int | None
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None
    extra_body: Mapping[str, Any] | None


class ArkLLMResponse(TypedDict):
    output: str
    reasoning_content: str | None
    ai_message: AIMessage


def prepareLLM(
    model: Literal["DOUBAO_2_0_LITE", "DOUBAO_2_0_MINI"],
    options: LLMOptions | None = None,
) -> ChatOpenAI:
    ARK_BASE_URL = os.getenv("ARK_BASE_URL", "")
    assert ARK_BASE_URL, "required 'ARK_BASE_URL' for AI Agent!!!"
    logger.info(f"LLM prepared")

    model_name = os.getenv(model, "")
    api_key = os.getenv("ARK_API_KEY", "")
    assert (
        model_name and api_key
    ), f"required '{model}' and 'ARK_API_KEY' for AI Agent!!!"

    model_args = {
        "model": model_name,
        "api_key": api_key,
        "base_url": ARK_BASE_URL,
    }
    callbacks = []
    options = options or {}

    llm = ChatOpenAI(**model_args, callbacks=callbacks, **options)
    return llm


async def ainvokeWithNoContext(
    llm: ChatOpenAI,
    prompt: str,
    images_urls: List[str] | None = None,
    system_prompt: str | None = None,
) -> str:
    """
    无上下文直接调用 LLM
    """
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    if images_urls:
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": url}} for url in images_urls
        ]
        messages.append(HumanMessage(content=content))
    else:
        messages.append(HumanMessage(content=prompt))
    resp = await llm.ainvoke(messages)
    return resp.content if resp else ""


# todo：暂不支持 ToolMessage
async def arkAinvoke(
    model: Literal["DOUBAO_2_0_LITE", "DOUBAO_2_0_MINI"],
    messages: List[BaseMessage],
    model_options: LLMOptions = {},
    reasoning_content_in_ai_message: bool = True,  # 是否把 reasoning_content 放到 ai_message 中
) -> ArkLLMResponse:
    """
    通过 Ark SDK ainvoke LLM
    """
    model_name = os.getenv(model, "")
    assert model_name, f"required '{model}' for AI Agent!!!"

    # 全局单例
    _ark_client = arkClient()

    reasoning_effort = model_options.get("reasoning_effort", None)
    resp = await _ark_client.responses.create(
        model=model_name,
        input=langchain2OpenAIChatMessages(
            messages=messages, is_ark_responses_messages=True
        ),
        temperature=model_options.get("temperature", None),
        max_output_tokens=model_options.get("max_tokens", None),
        reasoning=(
            {
                "effort": reasoning_effort,
            }
            if reasoning_effort
            else None
        ),
        extra_body=model_options.get("extra_body", None),
    )

    output_chunks: List[str] = []
    reasoning_chunks: List[str] = []
    for item in getattr(resp, "output", None) or []:
        item_type = getattr(item, "type", None)
        if item_type == "message":
            for block in getattr(item, "content", None) or []:
                text = getattr(block, "text", None)
                if isinstance(text, str) and text:
                    output_chunks.append(text)
        elif item_type == "reasoning":
            for summary in getattr(item, "summary", None) or []:
                text = getattr(summary, "text", None)
                if isinstance(text, str) and text:
                    reasoning_chunks.append(text)

    output_text = "\n".join(output_chunks)
    reasoning_content = "\n".join(reasoning_chunks)

    return {
        "output": output_text,
        "reasoning_content": reasoning_content,
        "ai_message": AIMessage(
            content=output_text,
            id=str(getattr(resp, "id", "")) or None,
            response_metadata={
                "model": getattr(resp, "model", None),
                "status": getattr(resp, "status", None),
                "reasoning_content": (
                    (reasoning_content or None)
                    if reasoning_content_in_ai_message
                    else None
                ),
            },
        ),
    }
