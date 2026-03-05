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


class PromptBundle(TypedDict):
    context_block: str
    final_prompt: str


class LLMOutput(TypedDict):
    message_candidates: List[str]  # 下一步消息候选
    risks: List[str]  # 风险提示
    suggestions: List[str]  # 下一步推进话题或行动建议
    message: str | None  # 错误消息


class GraphState(TypedDict):
    request: Request
    entities: Entities
    crush_profile_context: CrushProfileContext
    recall_queries: RecallQueries
    all_context: AllContext
    prompt_bundle: PromptBundle
    llm_output: LLMOutput


def initGraphState(request: Request) -> GraphState:
    return {
        "request": request,
        "entities": {
            "user": None,
            "crush": None,
            "relation_chain": None,
            "stage_histories": None,
        },
        "crush_profile_context": {
            "crush_mbti": None,
            "crush_profile": {},
        },
        "recall_queries": {
            "knowledge_query": None,
            "non_knowledge_query": None,
        },
        "all_context": {
            "knowledge": [],
            "event": [],
            "chat_topic": [],
            "derived_insight": [],
            "interaction_signal": [],
        },
        "prompt_bundle": {
            "context_block": "",
            "final_prompt": "",
        },
        "llm_output": {
            "message_candidates": [],
            "risks": [],
            "suggestions": [],
        },
    }
