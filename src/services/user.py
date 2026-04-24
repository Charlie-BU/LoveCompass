from urllib.parse import unquote
from sqlalchemy import or_
from jose import jwt
from jose.exceptions import JWTError
import os
import logging
from datetime import datetime, timedelta, timezone

from src.database.index import session
from src.database.models import User
from src.database.enums import Gender, parseEnum


logger = logging.getLogger(__name__)


def createAccessToken(
    data: dict, expires_delta: timedelta | None = timedelta(hours=24)
) -> str:
    """
    生成access token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    ALGORITHM = os.getenv("ALGORITHM")
    SECRET_KEY = os.getenv("LOGIN_SECRET")
    if not ALGORITHM or not SECRET_KEY:
        raise Exception("ALGORITHM or SECRET_KEY is not set in .env file")
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decodeAccessToken(token: str) -> dict:
    """
    解析access token
    """
    ALGORITHM = os.getenv("ALGORITHM")
    SECRET_KEY = os.getenv("LOGIN_SECRET")
    if not ALGORITHM or not SECRET_KEY:
        raise Exception("ALGORITHM or SECRET_KEY is not set in .env file")
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def getUserIdByAccessToken(
    token: str | None = None,
) -> int:
    """
    通过access token获取user id
    """
    if token is None:
        raise Exception("Access token is required")
    try:
        payload = decodeAccessToken(token)
    except JWTError as e:
        logger.warning(f"Decode access token failed: {str(e)}")
        raise Exception("Invalid or expired access token")
    id = payload.get("id")
    if not isinstance(id, int):
        raise Exception("Invalid access token payload")
    return id


def getUserById(
    id: int,
) -> dict:
    """
    通过user id获取user信息
    """
    with session() as db:
        user = db.get(User, id)
        if user is None:
            return {
                "status": -1,
                "message": "User not found",
            }
        return {
            "status": 200,
            "message": "Get user success",
            "user": user.toJson(include=["username", "nickname", "gender", "email"]),
        }


def getUserByUsernameOrNicknameOrEmail(
    username_or_nickname_or_email: str,
) -> dict:
    """
    通过用户名或昵称或邮箱获取用户信息
    """
    # 把 url 编码的字符串解码，否则是 %20 等格式
    keyword = unquote(username_or_nickname_or_email).strip()
    with session() as db:
        search_users = (
            db.query(User)
            .filter(
                or_(
                    User.username.ilike(f"%{keyword}%"),
                    User.nickname.ilike(f"%{keyword}%"),
                    User.email.ilike(f"%{keyword}%"),
                )
            )
            .order_by(User.nickname, User.username, User.email)
            .all()
        )
        return {
            "status": 200,
            "message": "Get users success",
            "users": [user.toJson() for user in search_users] if search_users else [],
        }


def userLogin(
    username: str,
    password: str,
) -> dict:
    """
    用户登录
    """
    username = username.strip()
    if username == "" or password == "":
        return {"status": -1, "message": "Username or password is empty"}

    with session() as db:
        user = (
            db.query(User)
            .filter(or_(User.username == username, User.email == username))
            .first()
        )
        if user is None:
            return {
                "status": -2,
                "message": "User not found",
            }
        if not user.checkPassword(password):
            return {
                "status": -3,
                "message": "Wrong password",
            }
        access_token = createAccessToken(
            data={"id": user.id, "username": user.username}
        )
        return {
            "status": 200,
            "message": "Login success",
            "access_token": access_token,
        }


def userRegister(
    username: str,
    nickname: str,
    gender: str,
    email: str,
    password: str,
) -> dict:
    """
    用户注册
    """
    username = username.strip()
    nickname = nickname.strip()
    email = email.strip()
    password = password.strip()
    if username == "":
        return {"status": -2, "message": "Username is empty"}
    if email == "":
        return {"status": -3, "message": "Email is empty"}
    if password == "":
        return {"status": -4, "message": "Password is empty"}
    if nickname == "":
        return {"status": -5, "message": "Nickname is empty"}

    with session() as db:
        existing_user = (
            db.query(User)
            .filter(or_(User.username == username, User.email == email))
            .first()
        )
        if existing_user:
            return {
                "status": -1,
                "message": "Username or email already registered",
            }
        try:
            gender: Gender = parseEnum(Gender, gender)
        except ValueError:
            return {"status": -6, "message": "Invalid gender"}
        user = User(
            username=username,
            nickname=nickname,
            gender=gender,
            email=email,
            password=User.hashPassword(password),
        )
        try:
            db.add(user)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Register failed: {str(e)}")
            return {"status": -7, "message": "Register failed"}
        return {
            "status": 200,
            "message": "Register success",
        }


def userModifyPassword(
    id: int,
    old_password: str,
    new_password: str,
) -> dict:
    """
    修改密码
    """
    if old_password == "":
        return {"status": -4, "message": "Old password is empty"}
    if new_password == "":
        return {"status": -5, "message": "New password is empty"}

    with session() as db:
        user = db.get(User, id)
        if user is None:
            return {
                "status": -1,
                "message": "User not found",
            }
        if not user.checkPassword(old_password):
            return {
                "status": -2,
                "message": "Wrong old password",
            }
        if old_password == new_password:
            return {
                "status": -3,
                "message": "New password cannot be the same as old password",
            }
        user.password = User.hashPassword(new_password)  # type: ignore
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Modify password failed, user_id={id}: {str(e)}")
            return {"status": -6, "message": "Modify password failed"}
        return {
            "status": 200,
            "message": "Modify password success",
        }


def userBindLark(
    user_id: int,
    lark_open_id: str,
) -> dict:
    """
    绑定飞书 openid
    """
    if not lark_open_id or lark_open_id.strip() == "":
        return {"status": -1, "message": "Lark open id is empty"}
    with session() as db:
        user = db.get(User, user_id)
        if user is None:
            return {"status": -2, "message": "User not found"}
        user.lark_open_id = lark_open_id
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Bind Lark failed, user_id={user_id}: {str(e)}")
            return {"status": -3, "message": "Bind Lark failed"}
        return {
            "status": 200,
            "message": "Bind Lark success",
        }
