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
    relation_chain_id: int | None
    conversation_screenshots: List[str] | None
    additional_context: str | None


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
    knowledge_vector: List[float]
    non_knowledge_vector: List[float]


class RecallResults(TypedDict):
    knowledge: List[Knowledge]
    event: List[Event]
    chat_topic: List[ChatTopic]
    derived_insight: List[DerivedInsight]


class RankedContext(TypedDict):
    interaction_signal: List[InteractionSignal]  # 这里再引入InteractionSignal
    items: List[dict]
    truncation_info: dict


class PromptBundle(TypedDict):
    system_prompt: str
    context_block: str
    user_prompt: str


class LLMOutput(TypedDict):
    reply_candidates: List[str]
    reasoning: str | None
    evidence: List[dict]  # 引用的证据项ID/来源


class GraphState(TypedDict):
    request: Request
    entities: Entities
    crush_profile_context: CrushProfileContext
    recall_queries: RecallQueries
    recall_results: RecallResults
    ranked_context: RankedContext
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
            "knowledge_vector": [],
            "non_knowledge_vector": [],
        },
        "recall_results": {
            "knowledge": [],
            "event": [],
            "chat_topic": [],
            "derived_insight": [],
        },
        "ranked_context": {
            "interaction_signal": [],
            "items": [],
            "truncation_info": {},
        },
        "prompt_bundle": {
            "system_prompt": "",
            "context_block": "",
            "user_prompt": "",
        },
        "llm_output": {
            "reply_candidates": [],
            "reasoning": None,
            "evidence": [],
        },
    }
