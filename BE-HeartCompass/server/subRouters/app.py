import json
import os
from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from ..services.user import userGetUserIdByAccessToken
from agent.graph.ContextGraph import getContextGraph
from agent.graph.AnalysisGraph import getAnalysisGraph
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
