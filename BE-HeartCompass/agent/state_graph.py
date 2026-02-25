# 模式2：StateGraph 工作流
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from typing import Annotated, Sequence, Optional, TypedDict
import os
import asyncio

from .llm import prepareLLM
from .prompt import getPrompt


class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    documents: list[str]
    context: str


# 全局单例
_graph_instance: Optional[CompiledStateGraph] = None
_graph_lock = asyncio.Lock()


async def node1(state: GraphState) -> dict:
    return state


async def node2(state: GraphState) -> dict:
    return state


async def node3(state: GraphState) -> dict:
    return state


async def getStateGraph() -> CompiledStateGraph:
    global _graph_instance
    if _graph_instance is not None:
        return _graph_instance
    # 双检查锁模式，确保线程安全
    async with _graph_lock:
        if _graph_instance is not None:
            return _graph_instance
        # todo: 放到节点中
        # system_prompt = await getPrompt(os.getenv("SYSTEM_PROMPT"))
        # llm: ChatOpenAI = prepareLLM()
        graph = StateGraph(GraphState)
        graph.add_node("node1", node1)
        graph.add_node("node2", node2)
        graph.add_node("node3", node3)

        graph.set_entry_point("node1")
        graph.add_edge("node1", "node2")
        graph.add_edge("node2", "node3")
        graph.add_edge("node3", END)

        _graph_instance = graph.compile()
        return _graph_instance
