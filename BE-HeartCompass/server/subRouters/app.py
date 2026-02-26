import json
from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from ..services.user import userGetUserIdByAccessToken
from database.database import session

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
    # user_id = userGetUserIdByAccessToken(request=request)
    chat_screenshot_urls = data["chat_screenshot_urls"]
    res = 123
    return res
