from robyn import SubRouter, Request, Response
from robyn.authentication import BearerGetter
import logging

from src.server.authentication import AuthHandler
from src.services.user import getUserById, getUserIdByAccessToken

logger = logging.getLogger(__name__)
user_router = SubRouter(__file__, prefix="/user")


# 全局异常处理
@user_router.exception
def handleException(error):
    logger.error(error)
    return Response(status_code=500, description="Internal Server Error", headers={})


# 鉴权中间件
user_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


@user_router.get("/getUserById", auth_required=True)
async def getUserByIdRouter(request: Request):
    """
    通过user id获取user信息
    """
    id = getUserIdByAccessToken(request)
    res = getUserById(id)
    return res
