from typing import List, TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState, add_messages


class Message(TypedDict):
    message: str
    relation_chain_id: int


class Request(TypedDict):
    user_id: int
    relation_chain_id: int
    messages_received: List[Message]  # 本轮收到的消息


class LLMOutput(TypedDict):
    messages_to_send: List[str]  # 本轮要发送的消息
    reasoning_content: str  # 本轮推理内容


class VirtualFigureGraphState(
    MessagesState
):  # 继承自MessagesState，自动包含messages: Annotated[list[AnyMessage], add_messages]字段
    request: Request
    context_block: str  # 关系与画像上下文
    words_to_user: str  # 非常重要，所以单独放在state顶层
    recalled_facts_from_db: str  # 根据本轮消息召回的Knowledge、Event、ChatTopic、InteractionSignal、DerivedInsight
    recalled_facts_from_viking: List[dict]  # Viking 记忆库召回的记忆
    llm_output: LLMOutput


class VirtualFigureGraphInput(TypedDict):
    request: Request


class VirtualFigureGraphOutput(TypedDict):
    llm_output: LLMOutput


def initVirtualFigureGraphState(request: Request) -> VirtualFigureGraphState:
    return {
        "request": request,
    }
