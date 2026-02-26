from datetime import datetime
from typing import List, TypedDict

from pydantic.type_adapter import P

from ...database.models import (
    Crush,
    RelationChain,
    User,
    Knowledge,
    Event,
    ChatLog,
    InteractionSignal,
    DerivedInsight,
)
from ...database.enums import MBTI, ChatChannel, ChatSpeaker


class RawChat(TypedDict):
    speaker: ChatSpeaker
    content: str
    timestamp: datetime
    channel: ChatChannel
    other_info: List[dict]  # 非Optional，空时为[]


class Request(TypedDict):
    user_id: int
    relation_chain_id: int | None
    chat_context: List[RawChat]
    mood: str | None


class Entities(TypedDict):
    user: User | None
    crush: Crush | None
    relation_chain: RelationChain | None


class CrushProfileContext(TypedDict):
    crush_mbti: MBTI | None
    crush_profile: dict  # 将 Crush 字段汇总、去噪、裁剪后的“可读画像摘要”


class RecallQueries(TypedDict):
    knowledge_query: str | None  # 从已知信息归一化
    non_knowledge_query: str | None  # 从已知信息归一化
    knowledge_vector: List[float]
    non_knowledge_vector: List[float]


class RecallResults(TypedDict):
    knowledge: List[Knowledge]
    event: List[Event]
    chat_log: List[ChatLog]
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
