# 办公网only，换方案

import os
import logging
from bytedance.fornax.integration.langchain import FornaxPromptHub


logger = logging.getLogger(__name__)

ENABLE_FORNAX_INTEGRATION = False


def is_enabled_fornax_sdk():
    return ENABLE_FORNAX_INTEGRATION


def init_fornax_sdk():
    global ENABLE_FORNAX_INTEGRATION
    if os.environ.get("FORNAX_AK", "") != "" or os.environ.get("FORNAX_SK", "") != "":
        ENABLE_FORNAX_INTEGRATION = True
    if not ENABLE_FORNAX_INTEGRATION:
        return
    from bytedance.fornax.integration.langchain import initialize

    try:
        initialize(
            os.environ.get("FORNAX_AK", ""),
            os.environ.get("FORNAX_SK", ""),
            fornax_custom_region="CN",
        )
        logger.info("Fornax SDK initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize Fornax SDK:%s", str(e))
        ENABLE_FORNAX_INTEGRATION = False


def get_prompt(prompt_key: str):
    # 根据prompt key获取fornax prompt实例化对象
    prompt = FornaxPromptHub.get_chat_prompt_messages(prompt_key)
    if len(prompt) == 0:
        logger.error("Failed to get prompt:%s", prompt_key)
        return None
    return prompt


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    init_fornax_sdk()
    print(get_prompt("charlie.fornax.heartcompass")[0][1])
