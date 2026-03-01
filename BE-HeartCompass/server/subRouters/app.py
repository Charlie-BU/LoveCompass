import os
from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from ..services.user import userGetUserIdByAccessToken
from database.database import session
from agent.graph.index import getStateGraph
from agent.graph.state import initGraphState


app_router = SubRouter(__file__, prefix="/app")


# 全局异常处理
@app_router.exception
def handleException(error):
    return Response(status_code=500, description=f"error msg: {error}", headers={})


# 鉴权中间件
app_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


@app_router.post("/getIntelligentReply", auth_required=True)
async def getIntelligentReply(request: Request):
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
    graph = await getStateGraph()
    initial_state = initGraphState(
        {
            "user_id": user_id,
            "relation_chain_id": relation_chain_id,
            "conversation_screenshots": list(conversation_screenshots),
            "additional_context": additional_context,
        }
    )
    result = await graph.ainvoke(initial_state)
    return result
