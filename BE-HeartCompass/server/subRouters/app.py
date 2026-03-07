import os
from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from ..services.app import appConversationAnalysis, appNarrativeAnalysis
from ..services.user import userGetUserIdByAccessToken


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
    # todo: 删除dev豁免
    user_id = (
        userGetUserIdByAccessToken(request=request)
        if os.getenv("CURRENT_ENV") != "dev"
        else 1
    )
    relation_chain_id = data["relation_chain_id"]
    conversation_screenshots = data["conversation_screenshots"]
    crush_name = data[
        "crush_name"
    ]  # todo：【FE】必须要求用户明确给出对方在截图中出现的姓名或位置（左侧/右侧）
    additional_context = data.get(
        "additional_context", ""
    )
    res = await appConversationAnalysis(
        user_id=user_id,
        relation_chain_id=int(relation_chain_id),
        conversation_screenshots=conversation_screenshots,
        crush_name=crush_name,
        additional_context=additional_context,
    )
    return res


# 自然语言叙述分析
@app_router.post("/narrativeAnalysis", auth_required=True)
async def narrativeAnalysis(request: Request):
    data = request.json()
    # todo: 删除dev豁免
    user_id = (
        userGetUserIdByAccessToken(request=request)
        if os.getenv("CURRENT_ENV") != "dev"
        else 1
    )
    relation_chain_id = data["relation_chain_id"]
    narrative = data["narrative"]
    res = await appNarrativeAnalysis(
        user_id=user_id,
        relation_chain_id=int(relation_chain_id),
        narrative=narrative,
    )
    return res
