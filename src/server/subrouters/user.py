from robyn import SubRouter, Request, Response
from robyn.authentication import BearerGetter
import logging

from src.server.authentication import AuthHandler
from src.services.user import (
    getUserById,
    getUserIdByAccessToken,
    getUserIdByOpenId,
    userLogin,
    userRegister,
    userModifyPassword,
    userBindLark,
)

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
    return getUserById(id)


# @user_router.get("/getUserByUsernameOrNicknameOrEmail", auth_required=True)
# async def getUserByUsernameOrNicknameOrEmailRouter(request: Request):
#     """
#     通过用户名或昵称或邮箱搜索用户信息
#     """
#     keyword = request.query_params.get("keyword", None)
#     if not isinstance(keyword, str):
#         return {"status": -1, "message": "Invalid keyword"}
#     return getUserByUsernameOrNicknameOrEmail(keyword)


@user_router.get("/getUserIdByOpenId")
async def getUserIdByOpenIdRouter(request: Request):
    """
    通过飞书 openid 获取用户 id
    """
    open_id = request.query_params.get("open_id", None)
    if not open_id or not isinstance(open_id, str):
        return {"status": -1, "message": "Invalid open_id"}
    return getUserIdByOpenId(open_id)


@user_router.post("/userLogin")
async def userLoginRouter(request: Request):
    """
    用户登录
    """
    body = request.json()
    username = body.get("username", "")
    password = body.get("password", "")
    return userLogin(username=username, password=password)


@user_router.post("/userRegister")
async def userRegisterRouter(request: Request):
    """
    用户注册
    """
    body = request.json()
    return userRegister(
        username=body.get("username", ""),
        nickname=body.get("nickname", ""),
        gender=body.get("gender", ""),
        email=body.get("email", ""),
        password=body.get("password", ""),
    )


@user_router.post("/userModifyPassword", auth_required=True)
async def userModifyPasswordRouter(request: Request):
    """
    修改用户密码
    """
    body = request.json()
    id = getUserIdByAccessToken(request)
    return userModifyPassword(
        id=id,
        old_password=body.get("old_password", ""),
        new_password=body.get("new_password", ""),
    )


@user_router.post("/userBindLark", auth_required=True)
async def userBindLarkRouter(request: Request):
    """
    绑定飞书 openid
    """
    body = request.json()
    id = getUserIdByAccessToken(request)
    return userBindLark(
        user_id=id,
        lark_open_id=body.get("lark_open_id", ""),
    )
