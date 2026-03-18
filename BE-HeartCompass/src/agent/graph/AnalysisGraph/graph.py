from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import InMemorySaver
import logging

from src.agent.graph.AnalysisGraph.state import (
    AnalysisGraphInput,
    AnalysisGraphOutput,
    AnalysisGraphState,
)
from src.agent.graph.AnalysisGraph.nodes import (
    nodeFetchSystemPromptFromNarrative,
    nodeFetchSystemPromptFromScreenshots,
    nodeCallLLM,
)

logger = logging.getLogger(__name__)


def buildBaseAnalysisGraph() -> StateGraph:
    graph = StateGraph(
        state_schema=AnalysisGraphState,
        input_schema=AnalysisGraphInput,
        output_schema=AnalysisGraphOutput,
    )
    graph.add_node(
        "nodeFetchSystemPromptFromNarrative", nodeFetchSystemPromptFromNarrative
    )
    graph.add_node(
        "nodeFetchSystemPromptFromScreenshots", nodeFetchSystemPromptFromScreenshots
    )
    graph.add_node("nodeCallLLM", nodeCallLLM)

    # 路由到不同的节点
    def routerByType(state: AnalysisGraphState) -> str:
        req_type = state["request"].get("type")
        match req_type:
            case "conversation":
                return "nodeFetchSystemPromptFromScreenshots"
            case "narrative":
                return "nodeFetchSystemPromptFromNarrative"

    graph.add_conditional_edges(
        START,
        routerByType,
        {
            "nodeFetchSystemPromptFromScreenshots": "nodeFetchSystemPromptFromScreenshots",
            "nodeFetchSystemPromptFromNarrative": "nodeFetchSystemPromptFromNarrative",
        },
    )
    graph.add_edge("nodeFetchSystemPromptFromScreenshots", "nodeCallLLM")
    graph.add_edge("nodeFetchSystemPromptFromNarrative", "nodeCallLLM")
    graph.add_edge("nodeCallLLM", END)

    return graph
    # return graph.compile(checkpointer=InMemorySaver())


def buildAnalysisGraph() -> CompiledStateGraph:
    graph = buildBaseAnalysisGraph()
    return graph.compile()


def buildAnalysisGraphWithMemory() -> CompiledStateGraph:
    # todo: PostgresSaver 报500，暂用 InMemorySaver
    graph = buildBaseAnalysisGraph()
    return graph.compile(checkpointer=InMemorySaver())


# 全局单例：在模块导入时执行一次，进程内后续都复用同一个对象
AnalysisGraph = buildAnalysisGraphWithMemory()


def getAnalysisGraph() -> CompiledStateGraph:
    return AnalysisGraph
