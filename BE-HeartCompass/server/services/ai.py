import os
import json
from typing import List

from agent.prompt import getPrompt
from agent.llm import prepareLLM, ainvokeWithNoContext


# 对上下文记录或知识库条目进行摘要
async def summarizeContext(content: str) -> str:
    prompt = await getPrompt(
        os.getenv("SUMMARIZE_CONTENT"),
        {"content": content},
    )
    llm = prepareLLM(model="DOUBAO_2_0_MINI")
    return await ainvokeWithNoContext(
        llm=llm,
        prompt=prompt,
    )


# 将自然语言组织拆分与提炼为knowledge
async def extractKnowledge(content: str) -> str:
    prompt = await getPrompt(
        os.getenv("EXTRACT_KNOWLEDGE"),
        {"content": content},
    )
    llm = prepareLLM(model="DOUBAO_2_0_LITE")
    return await ainvokeWithNoContext(
        llm=llm,
        prompt=prompt,
    )


# 将自然语言的信息转为 crush_profile 和 event
async def extractContextFromNaturalLanguage(content: str, is_self: bool) -> str:
    prompt = await getPrompt(
        os.getenv(
            "EXTRACT_CONTEXT_FROM_NATURAL_LANGUAGE_SELF"
            if is_self
            else "EXTRACT_CONTEXT_FROM_NATURAL_LANGUAGE"
        ),
        {"content": content},
    )
    llm = prepareLLM(model="DOUBAO_2_0_LITE")
    return await ainvokeWithNoContext(
        llm=llm,
        prompt=prompt,
    )


# 从聊天记录截图中提取 chat_topic 和 crush_profile
async def extractContextFromScreenshots(
    screenshot_urls: List[str],
    additional_context: str,
    crush_name: str,
    username: str,
    is_self: bool,
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
        os.getenv(
            "EXTRACT_CONTEXT_FROM_SCREENSHOTS_SELF"
            if is_self
            else "EXTRACT_CONTEXT_FROM_SCREENSHOTS"
        ),
        {
            "crush_name": crush_name,
            "username": username,
            "additional_context": additional_context,
        },
    )
    llm = prepareLLM(model="DOUBAO_2_0_LITE")
    return await ainvokeWithNoContext(llm=llm, prompt=prompt, images_urls=cleaned_urls)


# 根据聊天记录截图、additional_context 和对方画像生成向量召回query
async def generateRecallQueriesFromScreenshots(
    screenshot_urls: List[str],
    crush_name: str,
    additional_context: str,
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
        os.getenv("GENERATE_RECALL_QUERIES_FROM_SCREENSHOTS"),
        {
            "crush_name": crush_name,  # 对方在截图中出现的姓名或位置（左侧/右侧）
            "additional_context": additional_context,
        },
    )
    llm = prepareLLM(model="DOUBAO_2_0_MINI")
    return await ainvokeWithNoContext(llm=llm, prompt=prompt, images_urls=cleaned_urls)


# 根据自然语言叙述和对方画像生成向量召回query
async def generateRecallQueriesFromNarrative(
    narrative: str,
) -> str:
    if not isinstance(narrative, str) or not narrative.strip():
        return "Wrong narrative format"
    prompt = await getPrompt(
        os.getenv("GENERATE_RECALL_QUERIES_FROM_NARRATIVE"),
        {
            "narrative": narrative.strip(),
        },
    )
    llm = prepareLLM(model="DOUBAO_2_0_MINI")
    return await ainvokeWithNoContext(
        llm=llm,
        prompt=prompt,
    )
