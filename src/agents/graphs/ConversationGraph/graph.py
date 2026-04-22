from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
import asyncio
import logging

from src.agents.graphs.ConversationGraph.state import (
    ConversationGraphInput,
    ConversationGraphOutput,
    ConversationGraphState,
)
from src.agents.graphs.ConversationGraph.nodes import (
    nodeBuildAndTrimMessage,
    nodeCallLLM,
    nodeLoadFRAndPersona,
    nodeRecallFeedsFromDB,
)
from src.agents.graphs.checkpointer import agetCheckpointer

logger = logging.getLogger(__name__)
_conversation_graph_instance: CompiledStateGraph | None = None
_conversation_graph_lock = asyncio.Lock()


def buildBaseConversationGraph() -> StateGraph:
    graph = StateGraph(
        state_schema=ConversationGraphState,
        input_schema=ConversationGraphInput,
        output_schema=ConversationGraphOutput,
    )

    graph.add_node("nodeLoadFRAndPersona", nodeLoadFRAndPersona)
    graph.add_node("nodeRecallFeedsFromDB", nodeRecallFeedsFromDB)
    graph.add_node("nodeBuildAndTrimMessage", nodeBuildAndTrimMessage)
    graph.add_node("nodeCallLLM", nodeCallLLM)

    graph.add_edge(START, "nodeLoadFRAndPersona")

    # nodeRecallFeedsFromDB 和 nodeBuildAndTrimMessage 并行执行
    graph.add_edge("nodeLoadFRAndPersona", "nodeRecallFeedsFromDB")
    graph.add_edge("nodeLoadFRAndPersona", "nodeBuildAndTrimMessage")
    graph.add_edge("nodeRecallFeedsFromDB", "nodeCallLLM")
    graph.add_edge("nodeBuildAndTrimMessage", "nodeCallLLM")
    graph.add_edge("nodeCallLLM", END)

    return graph


def buildConversationGraph() -> CompiledStateGraph:
    """
    构建无短期记忆的 ConversationGraph
    """
    graph = buildBaseConversationGraph()
    return graph.compile()


async def buildConversationGraphWithMemory() -> CompiledStateGraph:
    """
    构建有短期记忆的 ConversationGraph
    【注意】graph 中存在大量异步节点，必须使用异步 checkpointer，必须用 ainvoke 调用图
    """
    graph = buildBaseConversationGraph()
    checkpointer = await agetCheckpointer()
    return graph.compile(checkpointer=checkpointer)


async def getConversationGraph() -> CompiledStateGraph:
    global _conversation_graph_instance
    if _conversation_graph_instance is not None:
        return _conversation_graph_instance
    async with _conversation_graph_lock:
        if _conversation_graph_instance is None:
            _conversation_graph_instance = await buildConversationGraphWithMemory()
    return _conversation_graph_instance
