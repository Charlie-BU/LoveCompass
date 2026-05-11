import logging

from robyn import Request, Response, SubRouter
from robyn.authentication import BearerGetter

from src.server.auth import AuthHandler
from src.services.user import (
    getUserById,
    getUserIdByAccessToken,
    userBindLark,
    userLogin,
    userModifyPassword,
    userRegister,
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
    通过 user id 获取 user 信息
    """
    id = getUserIdByAccessToken(request=request)
    res = getUserById(id)
    return res


# @user_router.get("/getUserByUsernameOrNicknameOrEmail", auth_required=True)
# async def getUserByUsernameOrNicknameOrEmailRouter(request: Request):
#     """
#     通过用户名或昵称或邮箱获取用户信息
#     """
#     keyword = request.query_params.get("keyword", None)
#     if keyword is None or not isinstance(keyword, str):
#         return {"status": -1, "message": "Keyword is required", "users": []}
#     res = getUserByUsernameOrNicknameOrEmail(keyword)
#     return res


@user_router.post("/login")
async def userLoginRouter(request: Request):
    """
    用户登录
    """
    body = request.json()
    username = body.get("username", "")
    password = body.get("password", "")
    if not isinstance(username, str) or not isinstance(password, str):
        return {"status": -1, "message": "Username or password is invalid"}
    res = userLogin(username=username, password=password)
    return res


@user_router.post("/register")
async def userRegisterRouter(request: Request):
    """
    用户注册
    """
    body = request.json()
    username = body.get("username", "")
    nickname = body.get("nickname", "")
    gender = body.get("gender", "")
    email = body.get("email", "")
    password = body.get("password", "")
    if (
        not isinstance(username, str)
        or not isinstance(nickname, str)
        or not isinstance(gender, str)
        or not isinstance(email, str)
        or not isinstance(password, str)
    ):
        return {"status": -1, "message": "Register args are invalid"}
    res = userRegister(
        username=username,
        nickname=nickname,
        gender=gender,
        email=email,
        password=password,
    )
    return res


@user_router.post("/modifyPassword", auth_required=True)
async def userModifyPasswordRouter(request: Request):
    """
    修改当前用户密码
    """
    body = request.json()
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")
    if not isinstance(old_password, str) or not isinstance(new_password, str):
        return {"status": -1, "message": "Old password or new password is invalid"}

    user_id = getUserIdByAccessToken(request=request)
    res = userModifyPassword(
        id=user_id,
        old_password=old_password,
        new_password=new_password,
    )
    return res


@user_router.post("/bindLark", auth_required=True)
async def userBindLarkRouter(request: Request):
    """
    绑定当前用户飞书 openid
    """
    body = request.json()
    lark_open_id = body.get("lark_open_id", "")
    if not isinstance(lark_open_id, str):
        return {"status": -1, "message": "Lark open id is invalid"}

    user_id = getUserIdByAccessToken(request=request)
    res = userBindLark(user_id=user_id, lark_open_id=lark_open_id)
    return res
