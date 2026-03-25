from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import InMemorySaver
import logging

from src.agent.graph.VirtualFigureGraph.state import (
    VirtualFigureGraphState,
    VirtualFigureGraphInput,
    VirtualFigureGraphOutput,
)
from src.agent.graph.VirtualFigureGraph.nodes import (
    nodeInitState,
    nodeLoadPersona,
    nodeRecallFromDB,
    nodeRecallFromViking,
    nodeBuildMessage,
    nodeCallLLM,
)
from src.agent.graph.checkpointer import getCheckpointer

logger = logging.getLogger(__name__)


def buildBaseVirtualFigureGraph() -> StateGraph:
    graph = StateGraph(
        state_schema=VirtualFigureGraphState,
        input_schema=VirtualFigureGraphInput,
        output_schema=VirtualFigureGraphOutput,
    )
    graph.add_node("nodeInitState", nodeInitState)
    graph.add_node("nodeLoadPersona", nodeLoadPersona)
    graph.add_node("nodeRecallFromDB", nodeRecallFromDB)
    graph.add_node("nodeRecallFromViking", nodeRecallFromViking)
    graph.add_node("nodeBuildMessage", nodeBuildMessage)
    graph.add_node("nodeCallLLM", nodeCallLLM)

    graph.add_edge(START, "nodeInitState")
    # 四链路并行
    graph.add_edge("nodeInitState", "nodeLoadPersona")
    graph.add_edge("nodeInitState", "nodeRecallFromDB")
    graph.add_edge("nodeInitState", "nodeRecallFromViking")
    graph.add_edge("nodeInitState", "nodeBuildMessage")

    # 汇聚
    graph.add_edge(
        [
            "nodeLoadPersona",
            "nodeRecallFromDB",
            "nodeRecallFromViking",
            "nodeBuildMessage",
        ],
        "nodeCallLLM",
    )
    graph.add_edge("nodeCallLLM", END)

    return graph


def buildVirtualFigureGraph() -> CompiledStateGraph:
    graph = buildBaseVirtualFigureGraph()
    return graph.compile()


def buildVirtualFigureGraphWithMemory() -> CompiledStateGraph:
    # todo: PostgresSaver 报500，暂用 InMemorySaver
    graph = buildBaseVirtualFigureGraph()
    return graph.compile(checkpointer=InMemorySaver())
    # return graph.compile(checkpointer=getCheckpointer())


# 全局单例：在模块导入时执行一次，进程内后续都复用同一个对象
# VirtualFigureGraph = buildVirtualFigureGraph()
VirtualFigureGraph = buildVirtualFigureGraphWithMemory()


def getVirtualFigureGraph() -> CompiledStateGraph:
    return VirtualFigureGraph
