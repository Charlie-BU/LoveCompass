from agent.react_agent import getAgent, askWithNoContext
from agent.prompt import getPrompt


# 对上下文记录或知识库条目进行摘要
async def summarizeContext(content: str) -> str:
    prompt = await getPrompt(
        "https://www.prompt-minder.com/share/58962157-c1a3-4c6c-a37c-b151de2bc5e1",
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
        "https://www.prompt-minder.com/share/ebb2e5e8-3ea9-4122-b272-74cdd74d68cb",
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
        "https://www.prompt-minder.com/share/8e36f272-7f64-4210-b511-a9ee6b47bf00",
        {"content": content},
    )
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent,
        prompt=prompt,
    )
