from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
import asyncio
import logging

from .state import (
    VirtualFigureGraphState,
    VirtualFigureGraphInput,
    VirtualFigureGraphOutput,
)
from .nodes import (
    nodeLoadPersona,
    nodeRecallFromDB,
    nodeRecallFromMem0,
    nodeBuildMessage,
    nodeCallLLM,
)
from ..checkpointer import agetCheckpointer


logger = logging.getLogger(__name__)


# 全局单例
_virtual_figure_graph_instance: CompiledStateGraph | None = None
_virtual_figure_graph_lock = asyncio.Lock()


async def getVirtualFigureGraph() -> CompiledStateGraph:
    global _virtual_figure_graph_instance
    if _virtual_figure_graph_instance is not None:
        return _virtual_figure_graph_instance
    async with _virtual_figure_graph_lock:
        if _virtual_figure_graph_instance is not None:
            return _virtual_figure_graph_instance

        graph = StateGraph(
            state_schema=VirtualFigureGraphState,
            input_schema=VirtualFigureGraphInput,
            output_schema=VirtualFigureGraphOutput,
        )
        graph.add_node("nodeLoadPersona", nodeLoadPersona)
        graph.add_node("nodeRecallFromDB", nodeRecallFromDB)
        graph.add_node("nodeRecallFromMem0", nodeRecallFromMem0)
        graph.add_node("nodeBuildMessage", nodeBuildMessage)
        graph.add_node("nodeCallLLM", nodeCallLLM)

        graph.set_entry_point("nodeLoadPersona")
        graph.add_edge("nodeLoadPersona", "nodeRecallFromDB")
        graph.add_edge("nodeRecallFromDB", "nodeRecallFromMem0")
        graph.add_edge("nodeRecallFromMem0", "nodeBuildMessage")
        graph.add_edge("nodeBuildMessage", "nodeCallLLM")
        graph.add_edge("nodeCallLLM", END)

        # PostgresSaver实现短期记忆
        # todo：trim
        _virtual_figure_graph_instance = graph.compile(
            checkpointer=await agetCheckpointer()
        )
        return _virtual_figure_graph_instance
