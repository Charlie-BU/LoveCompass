from typing import List, TypedDict

from database.models import (
    User,
    Crush,
    RelationChain,
    ChainStageHistory,
    Knowledge,
    Event,
    ChatTopic,
    InteractionSignal,
    DerivedInsight,
)


class Request(TypedDict):
    user_id: int
    relation_chain_id: int
    # 情况1: 聊天记录分析
    conversation_screenshots: List[str] | None
    crush_name: str | None  # 对方在截图中出现的姓名或位置（左侧/右侧）
    additional_context: str | None
    # 情况2: 自然语言叙述分析
    narrative: str | None


class Entities(TypedDict):
    user: User | None
    crush: Crush | None
    relation_chain: RelationChain | None
    stage_histories: List[ChainStageHistory] | None


class CrushProfileContext(TypedDict):
    crush_mbti: str | None
    crush_profile: dict  # 将 Crush 字段汇总、去噪、裁剪后的“可读画像摘要”


class RecallQueries(TypedDict):
    knowledge_query: str | None  # 从已知信息归一化
    non_knowledge_query: str | None  # 从已知信息归一化


class AllContext(TypedDict):
    knowledge: List[Knowledge]
    event: List[Event]
    chat_topic: List[ChatTopic]
    derived_insight: List[DerivedInsight]
    interaction_signal: List[
        InteractionSignal
    ]  # 单独引入InteractionSignal，不走召回链路


class LLMOutput(TypedDict):
    message_candidates: List[str]  # 下一步消息候选
    risks: List[str]  # 风险提示
    suggestions: List[str]  # 下一步推进话题或行动建议
    message: str | None  # 错误消息


class ContextGraphState(TypedDict):
    request: Request
    context_block: str  # 关系与画像上下文


class AnalysisGraphInput(TypedDict):
    request: Request
    context_block: str  # 关系与画像上下文


class AnalysisGraphState(TypedDict):
    request: Request
    context_block: str  # 关系与画像上下文
    llm_output: LLMOutput


class AnalysisGraphOutput(TypedDict):
    llm_output: LLMOutput


def initContextGraphState(request: Request) -> ContextGraphState:
    return {
        "request": request,
        "context_block": "",
    }
