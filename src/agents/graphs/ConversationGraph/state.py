from typing import Annotated, Any, List, Literal, TypedDict
from langgraph.graph.message import MessagesState


class Request(TypedDict):
    user_id: int
    fr_id: int
    messages_received: List[str]  # 本轮收到的消息


class LLMOutput(TypedDict):
    messages_to_send: List[str]  # 本轮要发送的消息
    reasoning_content: str  # 本轮推理内容


class NodeLog(TypedDict, total=False):
    step: str
    status: Literal["ok", "skip", "error"]
    detail: str
    data: dict[str, Any]


def _mergeUniqueList(left: list[Any], right: list[Any]) -> list[Any]:
    """
    合并并去重列表，兼容并行分支同时写同一 channel 的场景
    """
    merged = []
    for item in (left or []) + (right or []):
        if item in merged:
            continue
        merged.append(item)
    return merged


class ConversationGraphState(
    MessagesState
):  # 继承自MessagesState，自动包含messages: Annotated[list[AnyMessage], add_messages]字段
    round_uuid: str  # 本轮次唯一标识 uuid
    
    request: Request
    user_name: str  # 用户姓名
    figure_and_relation: dict[str, Any]
    figure_persona: str  # 人物画像
    words_to_user: str  # 非常重要，单独提在 state 顶层

    recalled_personalities_from_db: str  # 根据本轮消息召回的 personality
    recalled_interaction_styles_from_db: str  # 根据本轮消息召回的 interaction style
    recalled_procedural_infos_from_db: str  # 根据本轮消息召回的 procedural info
    recalled_memories_from_db: str  # 根据本轮消息召回的 memory

    recalled_facts_from_viking: List[dict]  # Viking 记忆库召回的记忆

    conversation_summary: str  # 更早对话的滚动摘要
    logs: Annotated[list[NodeLog], _mergeUniqueList]
    warnings: Annotated[list[str], _mergeUniqueList]
    errors: Annotated[list[str], _mergeUniqueList]
    status: Literal["running", "failed", "completed"]
    llm_output: LLMOutput


class ConversationGraphInput(TypedDict):
    request: Request


class ConversationGraphOutput(TypedDict):
    llm_output: LLMOutput
