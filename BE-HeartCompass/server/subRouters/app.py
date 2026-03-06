import json
import os
from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from ..services.user import userGetUserIdByAccessToken
from agent.graph.ContextGraph import getContextGraph
from agent.graph.AnalysisGraph import getAnalysisGraph
from agent.graph.checkpointer import getCheckpointer
from agent.graph.state import (
    AnalysisGraphInput,
    AnalysisGraphOutput,
    ContextGraphState,
    initContextGraphState,
)
from database.database import session
from database.models import Analysis
from database.enums import AnalysisType


app_router = SubRouter(__file__, prefix="/app")


# 全局异常处理
@app_router.exception
def handleException(error):
    return Response(status_code=500, description=f"error msg: {error}", headers={})


# 鉴权中间件
app_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


# 聊天记录分析
@app_router.post("/conversationAnalysis", auth_required=True)
async def conversationAnalysis(request: Request):
    data = request.json()
    # todo: 鉴权+删除dev豁免
    user_id = (
        userGetUserIdByAccessToken(request=request)
        if os.getenv("CURRENT_ENV") != "dev"
        else 1
    )
    relation_chain_id = data["relation_chain_id"]
    conversation_screenshots = data["conversation_screenshots"]
    additional_context = data.get(
        "additional_context", ""
    )  # todo：【FE】必须要求用户明确给出聊天的双方哪位是用户自己，哪位是对方
    # 调用图
    context_graph = await getContextGraph()
    analysis_graph = await getAnalysisGraph()
    initial_state = initContextGraphState(
        {
            "user_id": user_id,
            "relation_chain_id": int(relation_chain_id),
            "conversation_screenshots": list(conversation_screenshots),
            "additional_context": additional_context,
        }
    )
    # 落库
    with session() as db:
        new_analysis = Analysis(
            relation_chain_id=int(relation_chain_id),
            type=AnalysisType.CONVERSATION,
            conversation_screenshots=list(conversation_screenshots),
            additional_context=additional_context,
            is_first_analysis=True,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

    short_term_memory_config = {
        "configurable": {"thread_id": f"{relation_chain_id}_{new_analysis.id}"}
    }
    # ContextGraph无需记忆
    context_state: ContextGraphState = await context_graph.ainvoke(initial_state)
    # AnalysisGraph需要记忆
    result: AnalysisGraphOutput = await analysis_graph.ainvoke(
        AnalysisGraphInput(**context_state, is_first_analysis=True, history_state=None),
        config=short_term_memory_config,
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
            db.commit()

    return {
        "status": 200,
        "message": "Success",
        "result": result["llm_output"],
        "analysis_id": new_analysis.id,
    }


# 自然语言叙述分析
@app_router.post("/narrativeAnalysis", auth_required=True)
async def narrativeAnalysis(request: Request):
    data = request.json()
    # todo: 鉴权+删除dev豁免
    user_id = (
        userGetUserIdByAccessToken(request=request)
        if os.getenv("CURRENT_ENV") != "dev"
        else 1
    )
    relation_chain_id = data["relation_chain_id"]
    narrative = data["narrative"]
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
    with session() as db:
        new_analysis = Analysis(
            relation_chain_id=int(relation_chain_id),
            type=AnalysisType.NARRATIVE,
            narrative=narrative,
            is_first_analysis=True,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

    short_term_memory_config = {
        "configurable": {"thread_id": f"{relation_chain_id}_{new_analysis.id}"}
    }
    # ContextGraph无需记忆
    context_state: ContextGraphState = await context_graph.ainvoke(initial_state)
    # AnalysisGraph需要记忆
    result: AnalysisGraphOutput = await analysis_graph.ainvoke(
        AnalysisGraphInput(**context_state, is_first_analysis=True, history_state=None),
        config=short_term_memory_config,
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
            db.commit()

    return {
        "status": 200,
        "message": "Success",
        "result": result["llm_output"],
        "analysis_id": new_analysis.id,
    }


# 基于分析记录短期记忆连续分析（无需重新调用ContextGraph）
@app_router.post("/continuousAnalysis", auth_required=True)
async def continuousAnalysis(request: Request):
    data = request.json()
    # todo: 鉴权+删除dev豁免
    user_id = (
        userGetUserIdByAccessToken(request=request)
        if os.getenv("CURRENT_ENV") != "dev"
        else 1
    )
    relation_chain_id = data["relation_chain_id"]
    base_analysis_id = data["analysis_id"]
    narrative = data["narrative"]

    # 调用图
    analysis_graph = await getAnalysisGraph()
    with session() as db:
        base_analysis = db.get(Analysis, int(base_analysis_id))
        if base_analysis is None or base_analysis.relation_chain_id != int(
            relation_chain_id
        ):
            return {
                "status": -1,
                "message": "analysis not found",
            }
        base_analysis_id_value = base_analysis.id
        new_analysis = Analysis(
            relation_chain_id=int(relation_chain_id),
            type=AnalysisType.NARRATIVE,
            narrative=narrative,
            is_first_analysis=False,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        new_analysis_id = new_analysis.id

    short_term_memory_config = {
        "configurable": {
            "thread_id": f"{relation_chain_id}_{base_analysis_id_value}"
        }  # 定位到base_analysis的记忆
    }
    checkpointer = await getCheckpointer()
    checkpoint_tuple = await checkpointer.aget_tuple(short_term_memory_config)
    if checkpoint_tuple is None:
        return {
            "status": -1,
            "message": "checkpoint not found",
        }
    if isinstance(checkpoint_tuple, dict):
        checkpoint = checkpoint_tuple.get("checkpoint") or {}
    else:
        checkpoint = checkpoint_tuple.checkpoint
    if isinstance(checkpoint, dict):
        channel_values = checkpoint.get("channel_values") or {}
    else:
        channel_values = checkpoint.channel_values or {}
    try:
        history_state = json.dumps(channel_values, ensure_ascii=False, default=str)
    except TypeError:
        history_state = str(channel_values)
    print("history_state\n", history_state)

    request_payload = {
        "user_id": user_id,
        "relation_chain_id": int(relation_chain_id),
        "conversation_screenshots": None,
        "additional_context": None,
        "narrative": narrative,
    }
    result: AnalysisGraphOutput = await analysis_graph.ainvoke(
        AnalysisGraphInput(
            request=request_payload,
            context_block="",
            is_first_analysis=False,
            history_state=history_state,
        ),
        config=short_term_memory_config,
    )
    with session() as db:
        analysis = db.get(Analysis, new_analysis_id)
        if analysis is not None:
            analysis.message_candidates = result["llm_output"].get(
                "message_candidates", []
            )
            analysis.risks = result["llm_output"].get("risks", [])
            analysis.suggestions = result["llm_output"].get("suggestions", [])
            db.commit()

    return result["llm_output"]
