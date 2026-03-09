from typing import List, TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class Message(TypedDict):
    message: str
    relation_chain_id: int


class Request(TypedDict):
    user_id: int
    relation_chain_id: int
    messages_received: List[Message]  # 本轮收到的消息


class Memory(TypedDict):
    messages: Annotated[
        List[BaseMessage], add_messages
    ]  # 存放SystemMessage、HumanMessage和AIMessage
    context_block: str  # 关系与画像上下文
    recalled_facts_from_db: str  # 根据本轮消息召回的Knowledge、Event、ChatTopic、InteractionSignal、DerivedInsight
    recalled_facts_from_mem0: List[dict]  # Mem0 记忆库召回的记忆


class LLMOutput(TypedDict):
    messages_to_send: List[str]  # 本轮要发送的消息
    thinking: str  # 本轮的思考过程


class VirtualFigureGraphState(TypedDict):
    request: Request
    memory: Memory
    llm_output: LLMOutput


class VirtualFigureGraphInput(TypedDict):
    request: Request
    llm_output: LLMOutput


class VirtualFigureGraphOutput(TypedDict):
    llm_output: LLMOutput


def initVirtualFigureGraphState(request: Request) -> VirtualFigureGraphState:
    return {
        "request": request,
    }


def resetVirtualFigureGraphState(request: Request) -> VirtualFigureGraphState:
    return {
        "request": request,
        "memory": {
            "messages": [],
            "context_block": "",
            "recalled_facts_from_db": "",
            "recalled_facts_from_mem0": [],
        },
        "llm_output": {
            "messages_to_send": [],
            "thinking": "",
        },
    }
