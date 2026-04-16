from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
import logging

from src.agents.graphs.FRBuildingGraph.nodes import (
    nodeBuildFRBuildingGraphOutput,
    nodeExtractFineGrainedFeeds,
    nodeExtractFRIntrinsicCandidates,
    nodeGenerateFRBuildingReport,
    nodeLoadFR,
    nodePersistFineGrainedFeedUpsert,
    nodePersistFRIntrinsicUpdate,
    nodePersistOriginalSource,
    nodePlanFineGrainedFeedUpsert,
    nodePlanFRIntrinsicUpdate,
    nodePreprocessInput,
)
from src.agents.graphs.FRBuildingGraph.state import (
    FRBuildingGraphInput,
    FRBuildingGraphOutput,
    FRBuildingGraphState,
)

logger = logging.getLogger(__name__)


def buildFRBuildingGraph() -> CompiledStateGraph:
    graph = StateGraph(
        state_schema=FRBuildingGraphState,
        input_schema=FRBuildingGraphInput,
        output_schema=FRBuildingGraphOutput,
    )

    graph.add_node("nodeLoadFR", nodeLoadFR)
    graph.add_node("nodePreprocessInput", nodePreprocessInput)
    graph.add_node("nodePersistOriginalSource", nodePersistOriginalSource)
    graph.add_node("nodeExtractFRIntrinsicCandidates", nodeExtractFRIntrinsicCandidates)
    graph.add_node("nodePlanFRIntrinsicUpdate", nodePlanFRIntrinsicUpdate)
    graph.add_node("nodePersistFRIntrinsicUpdate", nodePersistFRIntrinsicUpdate)
    graph.add_node("nodeExtractFineGrainedFeeds", nodeExtractFineGrainedFeeds)
    graph.add_node("nodePlanFineGrainedFeedUpsert", nodePlanFineGrainedFeedUpsert)
    graph.add_node("nodePersistFineGrainedFeedUpsert", nodePersistFineGrainedFeedUpsert)
    graph.add_node("nodeBuildFRBuildingGraphOutput", nodeBuildFRBuildingGraphOutput)
    graph.add_node("nodeGenerateFRBuildingReport", nodeGenerateFRBuildingReport)

    graph.add_edge(START, "nodeLoadFR")
    graph.add_edge("nodeLoadFR", "nodePreprocessInput")
    graph.add_edge("nodePreprocessInput", "nodePersistOriginalSource")
    # 步骤 5 与步骤 6 并行执行
    graph.add_edge("nodePersistOriginalSource", "nodeExtractFRIntrinsicCandidates")
    graph.add_edge("nodePersistOriginalSource", "nodeExtractFineGrainedFeeds")

    # 步骤 5
    graph.add_edge("nodeExtractFRIntrinsicCandidates", "nodePlanFRIntrinsicUpdate")
    graph.add_edge("nodePlanFRIntrinsicUpdate", "nodePersistFRIntrinsicUpdate")
    graph.add_edge("nodePersistFRIntrinsicUpdate", "nodeBuildFRBuildingGraphOutput")

    # 步骤 6
    graph.add_edge("nodeExtractFineGrainedFeeds", "nodePlanFineGrainedFeedUpsert")
    graph.add_edge("nodePlanFineGrainedFeedUpsert", "nodePersistFineGrainedFeedUpsert")
    graph.add_edge("nodePersistFineGrainedFeedUpsert", "nodeBuildFRBuildingGraphOutput")

    graph.add_edge("nodeBuildFRBuildingGraphOutput", "nodeGenerateFRBuildingReport")
    graph.add_edge("nodeGenerateFRBuildingReport", END)

    return graph.compile()


# 全局单例：在模块导入时执行一次，进程内后续都复用同一个对象
FRBuildingGraph = buildFRBuildingGraph()


def getFRBuildingGraph() -> CompiledStateGraph:
    return FRBuildingGraph
