import os
from datetime import datetime, timezone
from typing import List

from agent.react_agent import getAgent, askWithNoContext
from agent.prompt import getPrompt
from agent.graph.state import RawChat


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
async def normalizeContext(content: str) -> str:
    prompt = await getPrompt(
        os.getenv("NORMALIZE_CONTEXT_PROMPT"),
        {"content": content},
    )
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent,
        prompt=prompt,
    )


# todo: 效果极其不好且慢
# 从截图中提取聊天记录
async def extractChatFromScreenshots(screenshot_urls: List[str]) -> str:
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

    today = datetime.now(timezone.utc).date().isoformat()
    prompt = await getPrompt(
        os.getenv("EXTRACT_CHAT_FROM_SCREENSHOTS_PROMPT"),
        {"today": today},
    )
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent,
        prompt=prompt,
        images_urls=cleaned_urls,
    )


if __name__ == "__main__":
    import asyncio

    print(
        asyncio.run(
            extractChatFromScreenshots(
                [
                    "https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/1_73a3118bda.png",
                    "https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/2_720768c513.png",
                ]
            )
        )
    )
