import asyncio
import os
import threading
import inspect
from typing import Any, Awaitable, Callable, TypeVar

from src.utils.request import afetch

# todo

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
        "auth_required": False,
    },
    "userLogin": {
        "method": "POST",
        "path": "/user/userLogin",
        "auth_required": False,
    },
    "userRegister": {
        "method": "POST",
        "path": "/user/userRegister",
        "auth_required": False,
    },
    "userModifyPassword": {
        "method": "POST",
        "path": "/user/userModifyPassword",
        "auth_required": True,
    },
    "userBindLark": {
        "method": "POST",
        "path": "/user/userBindLark",
        "auth_required": True,
    },
    # fr_router
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
    "frBelongsToUser": {
        "method": "GET",
        "path": "/fr/frBelongsToUser",
        "auth_required": True,
    },
    "getFRAccessContextByOpenId": {
        "method": "GET",
        "path": "/fr/getFRAccessContextByOpenId",
        "auth_required": False,
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
    "getFROverallUpdateLogsThisRound": {
        "method": "GET",
        "path": "/fr/getFROverallUpdateLogsThisRound",
        "auth_required": True,
    },
    # feed_router
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
        "method": "POST",
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


def _isSharedDatabaseMode() -> bool:
    """
    判断是否使用共享数据库模式
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


def dispatchServiceCall(
    service: Callable[..., dict[str, Any]], args: dict[str, Any]
) -> dict[str, Any]:
    """
    调用服务接口，按照是否是共享数据库模式分发请求到本地服务或远程 http 服务
    """
    # 延迟导入，避免循环依赖
    from src.cli.utils import getCurrentUserFromLocalSession

    if not _isSharedDatabaseMode():
        local_result = service(**args)
        # 本地模式下，service 可能是同步或异步函数，需要统一转换为同步对象
        if inspect.isawaitable(local_result):
            return _runAwaitableSync(lambda: local_result)
        return local_result

    service_name = service.__name__
    service_config = SERVICE_API_MAP.get(service_name)
    if service_config is None:
        raise KeyError(f"Service `{service_name}` is not configured in SERVICE_API_MAP")

    base_url = _resolveServiceBaseURL()
    url = f"{base_url}{service_config['path']}"
    method = service_config["method"]

    headers: dict[str, str] = {}
    if service_config["auth_required"]:
        access_token = getCurrentUserFromLocalSession()["access_token"]
        headers["Authorization"] = f"Bearer {access_token}"

    def _send() -> Awaitable[dict[str, Any]]:
        if method == "GET":
            return afetch(url, method=method, query_params=args, headers=headers)
        return afetch(url, method=method, json_data=args, headers=headers)

    response = _runAwaitableSync(_send)
    body = response.get("body")
    if not isinstance(body, dict):
        return {"status": response.get("status_code", -1), "message": str(body)}
    return body


# if __name__ == "__main__":
#     import dotenv
#     from src.cli.constants import IMMORTALITY_ENV_PATH
#     from src.services.user import getUserById

#     dotenv.load_dotenv(IMMORTALITY_ENV_PATH)
#     print(dispatchServiceCall(getUserById, {"id": 1}))