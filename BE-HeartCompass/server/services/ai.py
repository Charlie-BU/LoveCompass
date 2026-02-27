import os
from datetime import datetime, timezone
from typing import List

from agent.react_agent import getAgent, askWithNoContext
from agent.prompt import getPrompt


# 对上下文记录或知识库条目进行摘要
async def summarizeContext(content: str) -> str:
    prompt = await getPrompt(
        os.getenv("SUMMARIZE_CONTENT_PROMPT"),
        {"content": content},
    )
    print(prompt)
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent,
        prompt=prompt,
    )


# 将自然语言组织拆分与提炼为knowledge
async def extractKnowledge(content: str) -> str:
    prompt = await getPrompt(
        os.getenv("EXTRACT_KNOWLEDGE_PROMPT"),
        {"content": content},
    )
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent,
        prompt=prompt,
    )


# 将自然语言的信息转为 crush_profile 和 event
async def extractContextFromNaturalLanguage(content: str) -> str:
    prompt = await getPrompt(
        os.getenv("NORMALIZE_CONTEXT_PROMPT"),
        {"content": content},
    )
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent,
        prompt=prompt,
    )


# 从聊天记录截图中提取 chat_topic 和 crush_profile
async def extractContextFromScreenshots(
    screenshot_urls: List[str],
    additional_context: str,
    crush_name: str,
    username: str,
) -> str:
    if not isinstance(screenshot_urls, list) or len(screenshot_urls) == 0:
        return "Wrong screenshot format"
    if len(screenshot_urls) > 5:
        return "Screenshots should be no more than 5"
    cleaned_urls: List[str] = []
    for url in screenshot_urls:
        if not isinstance(url, str):
            return "Wrong screenshot url"
        url = url.strip()
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return "Wrong screenshot url"
        cleaned_urls.append(url)

    prompt = await getPrompt(
        os.getenv("EXTRACT_CONTEXT_FROM_SCREENSHOTS"),
        {
            "crush_name": crush_name,
            "username": username,
            "additional_context": additional_context,
        },
    )
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent, prompt=prompt, images_urls=cleaned_urls
    )


# # 从截图中提取聊天记录：效果极其不好且慢
# async def extractChatFromScreenshots(screenshot_urls: List[str]) -> str:
#     if not isinstance(screenshot_urls, list) or len(screenshot_urls) == 0:
#         return "Wrong screenshot format"
#     if len(screenshot_urls) > 5:
#         return "Screenshots should be no more than 5"
#     cleaned_urls: List[str] = []
#     for url in screenshot_urls:
#         if not isinstance(url, str):
#             return "Wrong screenshot url"
#         url = url.strip()
#         if not url or not (url.startswith("http://") or url.startswith("https://")):
#             return "Wrong screenshot url"
#         cleaned_urls.append(url)

#     today = datetime.now(timezone.utc).date().isoformat()
#     prompt = await getPrompt(
#         os.getenv("EXTRACT_CHAT_FROM_SCREENSHOTS_PROMPT"),
#         {"today": today},
#     )
#     agent = await getAgent()
#     return await askWithNoContext(
#         react_agent=agent,
#         prompt=prompt,
#         images_urls=cleaned_urls,
#     )


# TEST: uv run -m server.services.ai
if __name__ == "__main__":
    import asyncio
    import json
    import time

    start = time.perf_counter()
    res = asyncio.run(
        extractContextFromScreenshots(
            [
                "https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_5095a6fc17.png",
                "https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/c32cc20f89699777e53b41be55d11279_07894cb3e4.jpg",
            ],
            "浔～溯",
        )
    )
    print(json.dumps(json.loads(res), ensure_ascii=False, indent=4))
    print(f"\nDuration(s):  {time.perf_counter() - start}")
