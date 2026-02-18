import os
from functools import lru_cache
from volcenginesdkarkruntime import AsyncArk


# 全局单例
@lru_cache
def arkClient():
    embedding_endpoint_id = os.getenv("EMBEDDING_ENDPOINT_ID", "")
    api_key = os.getenv("ENDPOINT_API_KEY", "")
    assert (
        embedding_endpoint_id and api_key
    ), "required 'EMBEDDING_ENDPOINT_ID' and 'ENDPOINT_API_KEY' for AI Agent!!!"

    client = AsyncArk(
        api_key=api_key,
    )
    return client
