import asyncio
import os
import threading
import inspect
import logging
from typing import Any, Awaitable, Callable, TypeVar

from src.utils.request import afetch

logger = logging.getLogger(__name__)


SERVICE_API_MAP = {
    # user_router
    "getUserById": {
        "method": "GET",
        "path": "/user/getUserById",
        "auth_required": True,
    },
    "getUserIdByOpenId": {
        "method": "GET",
        "path": "/user/getUserIdByOpenId",
        "auth_required": True,
    },
    "userLogin": {
        "method": "POST",
        "path": "/user/login",
        "auth_required": False,
    },
    "userRegister": {
        "method": "POST",
        "path": "/user/register",
        "auth_required": False,
    },
    "userModifyPassword": {
        "method": "POST",
        "path": "/user/modifyPassword",
        "auth_required": True,
    },
    "userBindLark": {
        "method": "POST",
        "path": "/user/bindLark",
        "auth_required": True,
    },
    # figure_and_relation_router
    "addFigureAndRelation": {
        "method": "POST",
        "path": "/fr/addFigureAndRelation",
        "auth_required": True,
    },
    "deleteFigureAndRelation": {
        "method": "POST",
        "path": "/fr/deleteFigureAndRelation",
        "auth_required": True,
    },
    "updateFigureAndRelation": {
        "method": "POST",
        "path": "/fr/updateFigureAndRelation",
        "auth_required": True,
    },
    "getFigureAndRelation": {
        "method": "GET",
        "path": "/fr/getFigureAndRelation",
        "auth_required": True,
    },
    "getAllFigureAndRelations": {
        "method": "GET",
        "path": "/fr/getAllFigureAndRelations",
        "auth_required": True,
    },
    "addFRBuildingGraphReport": {
        "method": "POST",
        "path": "/fr/addFRBuildingGraphReport",
        "auth_required": True,
    },
    "deleteFRBuildingGraphReport": {
        "method": "POST",
        "path": "/fr/deleteFRBuildingGraphReport",
        "auth_required": True,
    },
    "getFRBuildingGraphReport": {
        "method": "GET",
        "path": "/fr/getFRBuildingGraphReport",
        "auth_required": True,
    },
    "getAllFRBuildingGraphReport": {
        "method": "GET",
        "path": "/fr/getAllFRBuildingGraphReport",
        "auth_required": True,
    },
    "getFRAllContext": {
        "method": "GET",
        "path": "/fr/getFRAllContext",
        "auth_required": True,
    },
    "syncFeedsToFRCore": {
        "method": "POST",
        "path": "/fr/syncFeedsToFRCore",
        "auth_required": True,
    },
    "syncAllFeedsToFRCore": {
        "method": "POST",
        "path": "/fr/syncAllFeedsToFRCore",
        "auth_required": True,
    },
    "ifFRBelongsToUser": {
        "method": "GET",
        "path": "/fr/ifFRBelongsToUser",
        "auth_required": True,
    },
    # fine_grained_feed_router
    "addFineGrainedFeed": {
        "method": "POST",
        "path": "/feed/addFineGrainedFeed",
        "auth_required": True,
    },
    "deleteFineGrainedFeed": {
        "method": "POST",
        "path": "/feed/deleteFineGrainedFeed",
        "auth_required": True,
    },
    "updateFineGrainedFeed": {
        "method": "POST",
        "path": "/feed/updateFineGrainedFeed",
        "auth_required": True,
    },
    "getFineGrainedFeed": {
        "method": "GET",
        "path": "/feed/getFineGrainedFeed",
        "auth_required": True,
    },
    "getAllFineGrainedFeed": {
        "method": "GET",
        "path": "/feed/getAllFineGrainedFeed",
        "auth_required": True,
    },
    "recallFineGrainedFeeds": {
        "method": "POST",
        "path": "/feed/recallFineGrainedFeeds",
        "auth_required": True,
    },
    "addOriginalSource": {
        "method": "POST",
        "path": "/feed/addOriginalSource",
        "auth_required": True,
    },
    "deleteOriginalSource": {
        "method": "POST",
        "path": "/feed/deleteOriginalSource",
        "auth_required": True,
    },
    "getOriginalSource": {
        "method": "GET",
        "path": "/feed/getOriginalSource",
        "auth_required": True,
    },
    "getAllOriginalSource": {
        "method": "GET",
        "path": "/feed/getAllOriginalSource",
        "auth_required": True,
    },
    "addFineGrainedFeedConflict": {
        "method": "POST",
        "path": "/feed/addFineGrainedFeedConflict",
        "auth_required": True,
    },
    "hardDeleteFineGrainedFeedConflict": {
        "method": "POST",
        "path": "/feed/hardDeleteFineGrainedFeedConflict",
        "auth_required": True,
    },
    "resolveFineGrainedFeedConflict": {
        "method": "POST",
        "path": "/feed/resolveFineGrainedFeedConflict",
        "auth_required": True,
    },
    "getFineGrainedFeedConflict": {
        "method": "GET",
        "path": "/feed/getFineGrainedFeedConflict",
        "auth_required": True,
    },
    "getAllFineGrainedFeedConflict": {
        "method": "GET",
        "path": "/feed/getAllFineGrainedFeedConflict",
        "auth_required": True,
    },
    # knowledge_router
    "addKnowledgePiece": {
        "method": "POST",
        "path": "/knowledge/addKnowledgePiece",
        "auth_required": True,
    },
    "recallKnowledgePieces": {
        "method": "GET",
        "path": "/knowledge/recallKnowledgePieces",
        "auth_required": True,
    },
    "deleteKnowledgePiece": {
        "method": "POST",
        "path": "/knowledge/deleteKnowledgePiece",
        "auth_required": True,
    },
    "getKnowledgePiece": {
        "method": "GET",
        "path": "/knowledge/getKnowledgePiece",
        "auth_required": True,
    },
    "getAllKnowledgePieces": {
        "method": "GET",
        "path": "/knowledge/getAllKnowledgePieces",
        "auth_required": True,
    },
}

# todo: 待验证
GRAPH_API_MAP = {
    "runConversationGraph": {
        "method": "POST",
        "path": "/graph/conversation",
        "auth_required": True,
    },
    "runFRBuildingGraph": {
        "method": "POST",
        "path": "/graph/frBuilding",
        "auth_required": True,
    },
}


def isSharedDatabaseMode() -> bool:
    """
    判断当前是否使用共享数据库模式
    """
    return (os.getenv("USE_SHARED_DATABASE", "False") or "").strip().lower() == "true"


def _resolveServiceBaseURL() -> str:
    """
    解析 HTTP_BASE_URL
    """
    base_url = os.getenv("HTTP_BASE_URL")
    if not base_url:
        raise ValueError("HTTP_BASE_URL is empty")
    return base_url.rstrip("/")


T = TypeVar("T")


def _runAwaitableSync(awaitable_factory: Callable[..., Awaitable[T]]) -> T:
    """
    同步运行异步函数
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable_factory())

    result_box: dict[str, T] = {}
    error_box: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result_box["value"] = asyncio.run(awaitable_factory())
        except BaseException as err:  # pragma: no cover - propagated to caller
            error_box["error"] = err

    worker = threading.Thread(target=_runner, daemon=True)
    worker.start()
    worker.join()

    if "error" in error_box:
        raise error_box["error"]
    return result_box["value"]


def _buildAuthHeaders(auth_required: bool) -> dict[str, str]:
    """
    构造鉴权请求头
    """
    if not auth_required:
        return {}

    # 延迟导入，避免循环依赖
    from src.cli.utils import getCurrentUserFromLocalSession

    access_token = getCurrentUserFromLocalSession()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _requestHTTPByConfig(
    *,
    service_name: str,
    args: dict[str, Any],
    api_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    根据 API 配置发起 HTTP 请求
    """
    api_config = api_map.get(service_name)
    if api_config is None:
        raise KeyError(f"API `{service_name}` is not configured")

    base_url = _resolveServiceBaseURL()
    url = f"{base_url}{api_config['path']}"
    method = api_config["method"]
    headers = _buildAuthHeaders(api_config["auth_required"])

    def _send() -> Awaitable[dict[str, Any]]:
        if method == "GET":
            return afetch(url, method=method, query_params=args, headers=headers)
        return afetch(url, method=method, json_data=args, headers=headers)

    # 同步运行异步方法
    response = _runAwaitableSync(_send)
    body = response.get("body")
    if not isinstance(body, dict):
        return {"status": response.get("status_code", -1), "message": str(body)}
    return body


def dispatchServiceCall(
    service: Callable[..., dict[str, Any]], args: dict[str, Any]
) -> dict[str, Any]:
    """
    调用服务接口，按照是否是共享数据库模式分发请求到本地服务或远程 http API
    """
    if not isSharedDatabaseMode():
        # 非共享数据库模式，直接调用本地 service
        logger.info(
            f"Non-shared database mode, calling local service: {service.__name__}"
        )
        local_result = service(**args)
        # 本地模式下，service 可能是同步或异步函数，需要统一转换为同步对象
        if inspect.isawaitable(local_result):
            return _runAwaitableSync(lambda: local_result)
        return local_result

    # 共享数据库模式，发起 HTTP 请求
    logger.info(f"Shared database mode, calling remote service: {service.__name__}")
    service_name = service.__name__
    return _requestHTTPByConfig(
        service_name=service_name, args=args, api_map=SERVICE_API_MAP
    )


# if __name__ == "__main__":
#     import dotenv
#     from src.cli.constants import IMMORTALITY_ENV_PATH
#     from src.services.user import getUserById, userLogin

#     logging.basicConfig(
#         level=logging.INFO,
#         force=True,
#     )

#     dotenv.load_dotenv(IMMORTALITY_ENV_PATH)
#     print(dispatchServiceCall(userLogin, {"username": "", "password": ""}))
#     print(dispatchServiceCall(getUserById, {"id": 1}))
