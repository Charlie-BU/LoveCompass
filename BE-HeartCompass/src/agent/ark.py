import os
from functools import lru_cache
from volcenginesdkarkruntime import AsyncArk


# 全局单例
@lru_cache
def arkClient():
    api_key = os.getenv("ENDPOINT_API_KEY", "")
    assert api_key, "required 'ENDPOINT_API_KEY' for AI Agent!!!"

    client = AsyncArk(
        api_key=api_key,
    )
    return client
