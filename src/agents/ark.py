import os
from functools import lru_cache
from volcenginesdkarkruntime import AsyncArk


# 全局单例
@lru_cache
def arkClient() -> AsyncArk | None:
    api_key = os.getenv("ARK_API_KEY", "")
    if not api_key:
        return None

    client = AsyncArk(
        api_key=api_key,
    )
    return client
