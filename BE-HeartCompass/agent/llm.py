import logging
import os
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def prepare_llm() -> ChatOpenAI:
    ARK_BASE_URL = os.getenv("ARK_BASE_URL", "")
    assert ARK_BASE_URL, "required 'ARK_BASE_URL' for AI Agent!!!"
    logger.info(f"ARK_BASE_URL={ARK_BASE_URL}")

    endpoint_id = os.getenv("ENDPOINT_ID", "")
    api_key = os.getenv("ENDPOINT_API_KEY", "")

    assert (
        endpoint_id and api_key
    ), "required 'ENDPOINT_ID' and 'ENDPOINT_API_KEY' for AI Agent!!!"

    model_args = {
        "model": endpoint_id,
        "api_key": api_key,
        "base_url": ARK_BASE_URL,
    }
    callbacks = []

    llm = ChatOpenAI(**model_args, callbacks=callbacks)
    return llm
