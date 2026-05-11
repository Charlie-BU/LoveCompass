import os
from robyn import Request
from robyn.robyn import Identity
from robyn.authentication import AuthenticationHandler

from src.services.user import decodeAccessToken, getUserById


# 接口权限映射，value为访问该接口最低的用户等级
API_PERMISSION_MAP = {}


class AuthHandler(AuthenticationHandler):
    def authenticate(self, request: Request):
        # dev环境下，鉴权豁免
        if os.getenv("CURRENT_ENV") == "dev":
            return Identity(claims={"user": f"{ getUserById(1) }"})
        token = self.token_getter.get_token(request)
        try:
            payload = decodeAccessToken(token or "")
            id = int(payload["id"])
        except Exception:
            return None
        user = getUserById(id).get("user")
        # 检查接口权限
        api_path = request.url.path
        user_level = user.get("level")
        if (
            api_path in API_PERMISSION_MAP
            and user_level.value > API_PERMISSION_MAP[api_path].value
        ):  # 在API_PERMISSION_MAP中，且用户等级低于最低要求，拒绝访问
            return None
        return Identity(claims={"user": f"{ user }"})
