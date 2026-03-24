from functools import lru_cache
import lark_oapi as lark
import os


# 全局单例
@lru_cache
def larkClient():
    app_id = os.getenv("LARK_APP_ID", "")
    app_secret = os.getenv("LARK_APP_SECRET", "")
    assert app_id and app_secret, "required 'LARK_APP_ID' and 'LARK_APP_SECRET' for Lark client!!!"

    client = (
        lark.Client.builder()
        .app_id(app_id)
        .app_secret(app_secret)
        .log_level(lark.LogLevel.DEBUG)
        .build()
    )
    return client
