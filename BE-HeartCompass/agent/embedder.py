import os
from langchain_openai import OpenAIEmbeddings


def prepare_embedder() -> OpenAIEmbeddings:
    ARK_BASE_URL = os.getenv("ARK_BASE_URL", "")
    assert ARK_BASE_URL, "required 'ARK_BASE_URL' for AI Agent!!!"
    embedding_endpoint_id = os.getenv("EMBEDDING_ENDPOINT_ID", "")
    api_key = os.getenv("ENDPOINT_API_KEY", "")

    assert (
        embedding_endpoint_id and api_key
    ), "required 'EMBEDDING_ENDPOINT_ID' and 'ENDPOINT_API_KEY' for AI Agent!!!"

    model_args = {
        "model": embedding_endpoint_id,
        "api_key": api_key,
        "base_url": ARK_BASE_URL,
    }

    embedder = OpenAIEmbeddings(**model_args)
    return embedder
