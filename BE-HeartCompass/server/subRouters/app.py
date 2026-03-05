import os
from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from ..services.user import userGetUserIdByAccessToken
from database.database import session
from agent.graph.index import getContextGraph, getAnalysisGraph
from agent.graph.state import initGraphState

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
    initial_state = initGraphState(
        {
            "user_id": user_id,
            "relation_chain_id": int(relation_chain_id),
            "conversation_screenshots": list(conversation_screenshots),
            "additional_context": additional_context,
        }
    )
    # 采用同一短期记忆空间，两graph共享记忆
    short_term_memory_config = {"configurable": {"thread_id": str(relation_chain_id)}}
    context_state = await context_graph.ainvoke(
        initial_state, config=short_term_memory_config
    )
    result = await analysis_graph.ainvoke(
        context_state, config=short_term_memory_config
    )
    return result


# 自然语言叙述分析
async def NarrativeAnalysis(request: Request):
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
    initial_state = initGraphState(
        {
            "user_id": user_id,
            "relation_chain_id": int(relation_chain_id),
            "narrative": narrative,
        }
    )
    # 采用同一短期记忆空间，两graph共享记忆
    short_term_memory_config = {"configurable": {"thread_id": str(relation_chain_id)}}
    context_state = await context_graph.ainvoke(
        initial_state, config=short_term_memory_config
    )
    result = await analysis_graph.ainvoke(
        context_state, config=short_term_memory_config
    )
    return result
