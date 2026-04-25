import os
from functools import lru_cache
import lark_oapi as lark


# 全局单例
@lru_cache
def larkClient() -> lark.Client | None:
    app_id = os.getenv("LARK_APP_ID", "")
    app_secret = os.getenv("LARK_APP_SECRET", "")

    if not app_id or not app_secret:
        return None

    client = (
        lark.Client.builder()
        .app_id(app_id)
        .app_secret(app_secret)
        .log_level(lark.LogLevel.DEBUG)
        .build()
    )
    return client
