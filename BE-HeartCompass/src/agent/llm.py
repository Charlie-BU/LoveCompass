import logging
import os
from typing import Literal, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


def prepareLLM(model: Literal["DOUBAO_2_0_LITE", "DOUBAO_2_0_MINI"]) -> ChatOpenAI:
    ARK_BASE_URL = os.getenv("ARK_BASE_URL", "")
    assert ARK_BASE_URL, "required 'ARK_BASE_URL' for AI Agent!!!"
    logger.info(f"ARK_BASE_URL={ARK_BASE_URL}")

    model_name = os.getenv(model, "")
    api_key = os.getenv("ENDPOINT_API_KEY", "")

    assert (
        model_name and api_key
    ), f"required '{model}' and 'ENDPOINT_API_KEY' for AI Agent!!!"

    model_args = {
        "model": model_name,
        "api_key": api_key,
        "base_url": ARK_BASE_URL,
    }
    callbacks = []

    llm = ChatOpenAI(**model_args, callbacks=callbacks)
    return llm


# 无上下文直接调用llm
async def ainvokeWithNoContext(
    llm: ChatOpenAI,
    prompt: str,
    images_urls: List[str] | None = None,
    system_prompt: str | None = None,
) -> str:
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
    resp = llm.invoke(messages)
    return resp.content if resp else ""
