from typing import Annotated, List, TypedDict, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState, add_messages


class Request(TypedDict):
    user_id: int
    relation_chain_id: int
    type: Literal["conversation", "narrative"]
    # 情况1: 聊天记录分析
    conversation_screenshots: List[str] | None
    crush_name: str | None  # 对方在截图中出现的姓名或位置（左侧/右侧）
    additional_context: str | None
    # 情况2: 自然语言叙述分析
    narrative: str | None


class LLMOutput(TypedDict):
    message_candidates: List[str]  # 下一步消息候选
    risks: List[str]  # 风险提示
    suggestions: List[str]  # 下一步推进话题或行动建议
    message: str | None  # 错误消息


class AnalysisGraphInput(TypedDict):
    request: Request
    context_block: str  # 关系与画像上下文


class AnalysisGraphState(
    MessagesState
):  # 继承自MessagesState，自动包含messages: Annotated[list[AnyMessage], add_messages]字段
    request: Request
    context_block: str  # 关系与画像上下文
    system_prompt: str
    llm_output: LLMOutput


class AnalysisGraphOutput(TypedDict):
    llm_output: LLMOutput
