from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from database.database import session
from ..services.user import (
    userGetUserIdByAccessToken,
    userLogin,
    userRegister,
    userGetUserById,
    userGetUserByUsernameOrNicknameOrEmail,
    userModifyPassword,
)

user_router = SubRouter(__file__, prefix="/user")


# 全局异常处理
@user_router.exception
def handleException(error):
    return Response(status_code=500, description=f"error msg: {error}", headers={})


# 鉴权中间件
user_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


# 通过用户id获取用户详情
@user_router.get("/getUserById", auth_required=True)
async def getUserById(request: Request):
    id = request.query_params.get("id", None)
    if not id:
        return Response(
            status_code=400,
            description="id is required",
            headers={},
        )
    with session() as db:
        res = userGetUserById(db=db, id=int(id))
    return res


# 通过access_token获取用户详情
@user_router.get("/getMyInfo", auth_required=True)
async def getMyInfo(request: Request):
    user_id = userGetUserIdByAccessToken(request=request)
    with session() as db:
        res = userGetUserById(db=db, id=user_id)
    return res


# 通过用户名或昵称或邮箱获取用户信息
@user_router.get("/getUserByUsernameOrNicknameOrEmail", auth_required=True)
async def getUserByUsernameOrNicknameOrEmail(request: Request):
    username_or_nickname_or_email = request.query_params.get(
        "username_or_nickname_or_email", None
    )
    if not username_or_nickname_or_email:
        return Response(
            status_code=400,
            description="username_or_nickname_or_email is required",
            headers={},
        )
    with session() as db:
        res = userGetUserByUsernameOrNicknameOrEmail(
            db=db,
            username_or_nickname_or_email=username_or_nickname_or_email,
        )
    return res


# 用户登录
@user_router.post("/login")
async def login(request: Request):
    data = request.json()
    username = data["username"]
    password = data["password"]
    with session() as db:
        res = userLogin(db=db, username=username, password=password)
    return res


# 用户注册
@user_router.post("/register")
async def register(request: Request):
    data = request.json()
    username = data["username"]
    nickname = data["nickname"]
    gender = data["gender"]
    email = data["email"]
    mbti = data["mbti"]
    password = data["password"]
    with session() as db:
        res = userRegister(
            db=db,
            username=username,
            nickname=nickname,
            gender=gender,
            email=email,
            mbti=mbti,
            password=password,
        )
    return res


# 修改密码
@user_router.post("/modifyPassword", auth_required=True)
async def modifyPassword(request: Request):
    data = request.json()
    id = userGetUserIdByAccessToken(request=request)
    old_password = data["old_password"]
    new_password = data["new_password"]
    with session() as db:
        res = userModifyPassword(
            db=db,
            id=id,
            old_password=old_password,
            new_password=new_password,
        )
    return res
