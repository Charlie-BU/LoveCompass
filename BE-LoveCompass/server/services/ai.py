from typing import Literal

from agent.index import get_agent, ask_with_no_context

ReactAgent = get_agent()


async def summarize_context(content: str, where: Literal["context", "knowledge"]) -> str:
    task_desc = "上下文记录(Context)" if where == "context" else "知识库条目(Knowledge)"

    prompt = f"""
    你是一个情感辅助系统的智能助理。请为以下{task_desc}生成一个精练且完整的摘要。

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
    return await ask_with_no_context(prompt, ReactAgent)
