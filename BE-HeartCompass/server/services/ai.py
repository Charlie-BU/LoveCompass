from typing import Literal

from agent.index import getAgent, askWithNoContext

ReactAgent = getAgent()


# 对上下文记录或知识库条目进行摘要
async def summarizeContext(content: str, where: Literal["context", "knowledge"]) -> str:
    task_desc = "上下文记录(Context)" if where == "context" else "知识库条目(Knowledge)"

    prompt = f"""
    请为以下{task_desc}生成一个精练且完整的摘要。

    **输入内容**（JSON格式）：
    {content}

    **摘要要求**：
    1. **完整性**：保留核心信息（如人物、时间、关键事件、强烈情感、具体偏好或规则）。
    2. **精练性**：去除冗余的JSON结构和无关修饰，使用自然语言描述，字数控制在50字以内（除非信息量极大）。
    3. **格式**：直接输出摘要文本，不要包含任何解释或Markdown标记。
    4. **场景适配**：
       - 若为对话：概括对话主题和情感氛围。
       - 若为画像/偏好：概括关键特征。
       - 若为规则/知识：概括核心逻辑。

    请直接输出摘要：
    """
    return await askWithNoContext(prompt, ReactAgent)


# 将自然语言的信息转为STATIC_PROFILE和STAGE_EVENT
async def normalizeContext(content: str) -> str:
    prompt = f"""
    你是信息抽取助手。给定用户在和crush交往过程中的一些自然语言描述，请理解并抽取其中的STATIC_PROFILE与STAGE_EVENT，仅输出JSON。

    **输入描述**：
    {content}

    **输出格式（ts表述）**：
{{
    // 对方的个人画像
    STATIC_PROFILE: {{
        mbti?: string;  // MBTI
        likes?: string[];  // 喜好
        dislikes?: string[];  // 不喜欢
        boundaries?: string[];  // 个人边界
        traits?: string[];  // 个人特点
        evidence?: string[];  // 支持证据
        others?: Record<string, string>;  // 其他信息
    }};
    // 事件
    STAGE_EVENT: {{
        event: string;  // 事件详细内容和经过
        date?: string;  // 事件日期
        summary: string;  // 事件概要
        outcome: "positive" | "neutral" | "negative" | "unknown";  // 结果导向
        additional_info?: Record<string, string>;  // 其他额外信息
    }};
}}

    **抽取规则**：
    1. 100%基于输入内容，不要编造。
    2. 仅在内容涉及 STATIC_PROFILE 时输出该部分。
    3. 仅在内容涉及 STAGE_EVENT 时输出该部分。
    4. 同时涉及两类时，输出两部分。
    5. 两类都未涉及时，输出空对象 {{}}。
    6. 未提及的信息不要输出该字段。
    7. STAGE_EVENT 必须输出 event 与 outcome；event 为事件详细内容和经过，需要尽可能详细；可通过内容推断结果导向，若无法推断结果导向，使用 "unknown"。
    8. date 使用原文日期表达；无日期则省略。
    9. likes/dislikes/boundaries/traits/evidence 必须是字符串数组。
    10. evidence 用简短、可核查的表述概括证据，不要原文复述或情绪化改写。
    11. summary 生成一个精炼且完整的摘要，保留核心信息，字数控制在50字以内（除非信息量极大）。
    12. others/additional_info 用键值对补充零散信息，键必须为英文，合理的键名。
    13. 直接输出JSON文本，不要包含任何解释或Markdown标记。

    请直接输出JSON：
"""

    return await askWithNoContext(prompt, ReactAgent)
