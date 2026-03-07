from typing import List

from agent.graph.ContextGraph import getContextGraph
from agent.graph.AnalysisGraph import getAnalysisGraph
from agent.graph.state import (
    AnalysisGraphInput,
    AnalysisGraphOutput,
    ContextGraphState,
    initContextGraphState,
)
from database.database import session
from database.models import RelationChain, Analysis
from database.enums import AnalysisType


async def appConversationAnalysis(
    user_id: int,
    relation_chain_id: int,
    conversation_screenshots: List[str],
    crush_name: str,
    additional_context: str,
):
    # 鉴权
    with session() as db:
        relation_chain = db.get(RelationChain, int(relation_chain_id))
        if relation_chain is None:
            return {
                "status": -1,
                "message": "Relation chain not found",
            }
        if relation_chain.user_id != user_id:
            return {
                "status": -2,
                "message": "You are not in this relation chain",
            }
        # 调用图
        context_graph = await getContextGraph()
        analysis_graph = await getAnalysisGraph()
        initial_state = initContextGraphState(
            {
                "user_id": user_id,
                "relation_chain_id": int(relation_chain_id),
                "conversation_screenshots": list(conversation_screenshots),
                "crush_name": crush_name,
                "additional_context": additional_context,
            }
        )
        # 落库
        new_analysis = Analysis(
            relation_chain_id=int(relation_chain_id),
            type=AnalysisType.CONVERSATION,
            conversation_screenshots=list(conversation_screenshots),
            additional_context=additional_context,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

    context_state: ContextGraphState = await context_graph.ainvoke(initial_state)
    result: AnalysisGraphOutput = await analysis_graph.ainvoke(
        AnalysisGraphInput(**context_state),
    )

    # 两阶段 session，避免ainvoke耗时操作长时间占用数据库连接
    with session() as db:
        analysis = db.get(Analysis, new_analysis.id)
        if analysis is not None:
            analysis.message_candidates = result["llm_output"].get(
                "message_candidates", []
            )
            analysis.risks = result["llm_output"].get("risks", [])
            analysis.suggestions = result["llm_output"].get("suggestions", [])
            analysis.context_block = context_state["context_block"]
            db.commit()

    return {
        "status": 200,
        "message": "Success",
        "analysis_id": new_analysis.id,
        "result": result["llm_output"],
    }


async def appNarrativeAnalysis(
    user_id: int,
    relation_chain_id: int,
    narrative: str,
):
    # 鉴权
    with session() as db:
        relation_chain = db.get(RelationChain, int(relation_chain_id))
        if relation_chain is None:
            return {
                "status": -1,
                "message": "Relation chain not found",
            }
        if relation_chain.user_id != user_id:
            return {
                "status": -2,
                "message": "You are not in this relation chain",
            }
        # 调用图
        context_graph = await getContextGraph()
        analysis_graph = await getAnalysisGraph()
        initial_state = initContextGraphState(
            {
                "user_id": user_id,
                "relation_chain_id": int(relation_chain_id),
                "narrative": narrative,
            }
        )
        # 落库
        new_analysis = Analysis(
            relation_chain_id=int(relation_chain_id),
            type=AnalysisType.NARRATIVE,
            narrative=narrative,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

    context_state: ContextGraphState = await context_graph.ainvoke(initial_state)
    result: AnalysisGraphOutput = await analysis_graph.ainvoke(
        AnalysisGraphInput(**context_state)
    )
    # 两阶段 session，避免ainvoke耗时操作长时间占用数据库连接
    with session() as db:
        analysis = db.get(Analysis, new_analysis.id)
        if analysis is not None:
            analysis.message_candidates = result["llm_output"].get(
                "message_candidates", []
            )
            analysis.risks = result["llm_output"].get("risks", [])
            analysis.suggestions = result["llm_output"].get("suggestions", [])
            analysis.context_block = context_state["context_block"]
            db.commit()

    return {
        "status": 200,
        "message": "Success",
        "analysis_id": new_analysis.id,
        "result": result["llm_output"],
    }
