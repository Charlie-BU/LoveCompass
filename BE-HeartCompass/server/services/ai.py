import os
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
