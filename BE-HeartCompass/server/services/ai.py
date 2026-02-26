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
    prompt = f"""
    你是知识条目拆分与提炼助手。输入可能是一段自然语言或 JSON 结构的事实/观点，请将其拆分为一条或多条可写入向量数据库用于后续召回的知识条目，仅输出 JSON 数组。

    **输入内容**：
    {content}

    **输出格式**：
    [
      {{
        "content": "string",
        "summary": "string",
        "weight": float
      }}
    ]

    **拆分与提炼规则**：
    1. 100%基于输入内容，不要编造或推测。
    2. 覆盖全部信息，任何内容都不能遗漏。
    3. 每条 content 必须是可独立检索的完整事实或观点，避免指代词。
    4. 按语义原子化拆分：一条仅表达一个核心事实、特征、结论或规则。
    5. 对 JSON 输入需展开为多条事实：键名与其对应含义要体现在 content 中。
    6. 允许保留原文关键短语，但要去冗余、去模板化重复。
    7. summary 为对 content 的极简概括，尽量短，保留检索关键词。
    8. weight 为 0-1 浮点数，表示重要性；核心定义/结论/高频主题更高，细节更低。
    9. 不输出空字段；不输出与事实无关的解释。
    10. 若未包含可抽取事实，输出空数组 []。
    11. 仅输出 JSON 数组文本，不要包含任何解释或 Markdown 标记。

    请直接输出 JSON 数组：
    """
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent,
        prompt=prompt,
    )


# 将自然语言的信息转为 crush_profile 和 event
async def normalizeContext(content: str) -> str:
    prompt = f"""
    你是信息抽取助手。给定用户在和crush交往过程中的一些自然语言描述，请理解并抽取其中的crush_profile（对方的个人画像）与event（事件），仅输出JSON。

    **输入描述**：
    {content}

    **输出格式（ts表述）**：
{{
    // 对方的个人画像
    crush_profile: {{
        likes?: string[];  // 喜好
        dislikes?: string[];  // 不喜欢
        boundaries?: string[];  // 个人边界
        traits?: string[];  // 个人特点
        other_info?: Record<string, string>;  // 其他信息
    }};
    // 事件
    event: {{
        content: string;  // 事件详细内容和经过
        date?: string;  // 事件日期
        summary: string;  // 事件概要
        outcome: "positive" | "neutral" | "negative" | "unknown";  // 结果导向
        other_info?: Record<string, string>;  // 其他额外信息
        weight: number;  // 事件权重（重要性）
    }};
}}

    **抽取规则**：
    1. 100%基于输入内容，不要编造。
    2. 仅在内容涉及 crush_profile 时输出该部分。
    3. 仅在内容涉及 event 时输出该部分。
    4. 同时涉及两类时，输出两部分。
    5. 两类都未涉及时，输出空对象 {{}}。
    6. 未提及的信息不要输出该字段。
    7. event 必须输出 content 与 outcome；content 为事件详细内容和经过，需要尽可能详细；可通过内容推断结果导向，若无法推断结果导向，使用 "unknown"。
    8. date 使用原文日期表达；无日期则省略。
    9. likes/dislikes/boundaries/traits 必须是字符串数组。
    10. summary 生成一个精炼且完整的摘要，保留核心信息，字数控制在50字以内（除非信息量极大）。
    11. other_info 用键值对补充零散信息，键必须为英文，合理的键名。
    12. weight 为 0-1 浮点数，表示重要性；请根据事件内容和上下文，判断事件的重要性。
    13. 直接输出JSON文本，不要包含任何解释或Markdown标记。

    请直接输出JSON：
"""
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent,
        prompt=prompt,
    )
