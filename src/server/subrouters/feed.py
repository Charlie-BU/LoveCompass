from robyn import SubRouter, Request, Response
from robyn.authentication import BearerGetter
import logging
import json

from src.server.authentication import AuthHandler
from src.services.user import getUserIdByAccessToken
from src.services.fine_grained_feed import (
    addFineGrainedFeed,
    deleteFineGrainedFeed,
    updateFineGrainedFeed,
    getFineGrainedFeed,
    getAllFineGrainedFeed,
    recallFineGrainedFeeds,
    addOriginalSource,
    deleteOriginalSource,
    getOriginalSource,
    getAllOriginalSource,
    addFineGrainedFeedConflict,
    hardDeleteFineGrainedFeedConflict,
    resolveFineGrainedFeedConflict,
    getFineGrainedFeedConflict,
    getAllFineGrainedFeedConflict,
)
from src.database.enums import (
    FineGrainedFeedDimension,
    FineGrainedFeedConfidence,
    OriginalSourceType,
    ConflictStatus,
    parseEnum,
)
from src.utils.index import toInt


logger = logging.getLogger(__name__)
feed_router = SubRouter(__file__, prefix="/feed")


@feed_router.exception
def handleException(error):
    logger.error(error)
    return Response(status_code=500, description="Internal Server Error", headers={})


feed_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


def _parseScope(scope) -> list[dict]:
    """
    解析 scope 字段，将每个 item.scope 转换相应枚举
    """
    if not isinstance(scope, list):
        return []
    parsed = []
    for item in scope:
        if not isinstance(item, dict):
            continue
        raw_scope = item.get("scope")
        if raw_scope == "all":
            scope_value = "all"
        else:
            scope_value = parseEnum(FineGrainedFeedDimension, raw_scope)
        parsed.append(
            {
                "scope": scope_value,
                "top_k": toInt(item.get("top_k")),
            }
        )
    return parsed


@feed_router.post("/addFineGrainedFeed", auth_required=True)
async def addFineGrainedFeedRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    return await addFineGrainedFeed(
        user_id=id,
        fr_id=toInt(body.get("fr_id")),  # type: ignore
        original_source_id=toInt(body.get("original_source_id")),  # type: ignore
        dimension=parseEnum(FineGrainedFeedDimension, body.get("dimension")),  # type: ignore
        confidence=parseEnum(FineGrainedFeedConfidence, body.get("confidence")),  # type: ignore
        content=body.get("content", ""),
        sub_dimension=body.get("sub_dimension"),
    )


@feed_router.post("/deleteFineGrainedFeed", auth_required=True)
async def deleteFineGrainedFeedRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    return deleteFineGrainedFeed(
        user_id=id,
        fr_id=toInt(body.get("fr_id")),  # type: ignore
        fine_grained_feed_id=toInt(body.get("fine_grained_feed_id")),  # type: ignore
    )


@feed_router.post("/updateFineGrainedFeed", auth_required=True)
async def updateFineGrainedFeedRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    return await updateFineGrainedFeed(
        user_id=id,
        fr_id=toInt(body.get("fr_id")),  # type: ignore
        fine_grained_feed_id=toInt(body.get("fine_grained_feed_id")),  # type: ignore
        new_original_source_id=toInt(body.get("new_original_source_id")),  # type: ignore
        new_content=body.get("new_content", ""),
        new_sub_dimension=body.get("new_sub_dimension"),
    )


@feed_router.get("/getFineGrainedFeed", auth_required=True)
async def getFineGrainedFeedRouter(request: Request):
    id = getUserIdByAccessToken(request)
    return getFineGrainedFeed(
        user_id=id,
        fr_id=toInt(request.query_params.get("fr_id", None)),  # type: ignore
        fine_grained_feed_id=toInt(request.query_params.get("fine_grained_feed_id", None)),  # type: ignore
    )


@feed_router.get("/getAllFineGrainedFeed", auth_required=True)
async def getAllFineGrainedFeedRouter(request: Request):
    id = getUserIdByAccessToken(request)
    return getAllFineGrainedFeed(
        user_id=id,
        fr_id=toInt(request.query_params.get("fr_id", None)),  # type: ignore
    )


@feed_router.post("/recallFineGrainedFeeds", auth_required=True)
async def recallFineGrainedFeedsRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    query = body.get("query")
    return await recallFineGrainedFeeds(
        user_id=id,
        fr_id=toInt(body.get("fr_id")),  # type: ignore
        scope=_parseScope(body.get("scope")),
        query=query if isinstance(query, str) else None,
    )


@feed_router.post("/addOriginalSource", auth_required=True)
async def addOriginalSourceRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    dimensions = body.get("included_dimensions")
    included_dimensions = []
    if isinstance(dimensions, list):
        included_dimensions = [
            parseEnum(FineGrainedFeedDimension, item) for item in dimensions
        ]
    return addOriginalSource(
        user_id=id,
        fr_id=toInt(body.get("fr_id")),  # type: ignore
        type=parseEnum(OriginalSourceType, body.get("type")),  # type: ignore
        confidence=parseEnum(FineGrainedFeedConfidence, body.get("confidence")),  # type: ignore
        included_dimensions=included_dimensions,  # type: ignore
        content=body.get("content", ""),
        approx_date=body.get("approx_date"),
    )


@feed_router.post("/deleteOriginalSource", auth_required=True)
async def deleteOriginalSourceRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    return deleteOriginalSource(
        user_id=id,
        fr_id=toInt(body.get("fr_id")),  # type: ignore
        original_source_id=toInt(body.get("original_source_id")),  # type: ignore
    )


@feed_router.get("/getOriginalSource", auth_required=True)
async def getOriginalSourceRouter(request: Request):
    id = getUserIdByAccessToken(request)
    return getOriginalSource(
        user_id=id,
        fr_id=toInt(request.query_params.get("fr_id", None)),  # type: ignore
        original_source_id=toInt(request.query_params.get("original_source_id", None)),  # type: ignore
    )


@feed_router.get("/getAllOriginalSource", auth_required=True)
async def getAllOriginalSourceRouter(request: Request):
    id = getUserIdByAccessToken(request)
    return getAllOriginalSource(
        user_id=id,
        fr_id=toInt(request.query_params.get("fr_id", None)),  # type: ignore
    )


@feed_router.post("/addFineGrainedFeedConflict", auth_required=True)
async def addFineGrainedFeedConflictRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    feed_ids = body.get("feed_ids")
    if not isinstance(feed_ids, list):
        feed_ids = []
    return addFineGrainedFeedConflict(
        user_id=id,
        fr_id=toInt(body.get("fr_id")),  # type: ignore
        dimension=parseEnum(FineGrainedFeedDimension, body.get("dimension")),  # type: ignore
        feed_ids=[toInt(item) for item in feed_ids],  # type: ignore
        old_value=body.get("old_value", ""),
        new_value=body.get("new_value", ""),
        conflict_detail=body.get("conflict_detail", ""),
        status=parseEnum(ConflictStatus, body.get("status"))  # type: ignore
        or ConflictStatus.PENDING,
    )


@feed_router.post("/hardDeleteFineGrainedFeedConflict", auth_required=True)
async def hardDeleteFineGrainedFeedConflictRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    return hardDeleteFineGrainedFeedConflict(
        user_id=id,
        fr_id=toInt(body.get("fr_id")),  # type: ignore
        fine_grained_feed_conflict_id=toInt(body.get("fine_grained_feed_conflict_id")),  # type: ignore
    )


@feed_router.post("/resolveFineGrainedFeedConflict", auth_required=True)
async def resolveFineGrainedFeedConflictRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    return resolveFineGrainedFeedConflict(
        user_id=id,
        fr_id=toInt(body.get("fr_id")),  # type: ignore
        fine_grained_feed_conflict_id=toInt(body.get("fine_grained_feed_conflict_id")),  # type: ignore
        status=parseEnum(ConflictStatus, body.get("status")),  # type: ignore
    )


@feed_router.get("/getFineGrainedFeedConflict", auth_required=True)
async def getFineGrainedFeedConflictRouter(request: Request):
    id = getUserIdByAccessToken(request)
    return getFineGrainedFeedConflict(
        user_id=id,
        fr_id=toInt(request.query_params.get("fr_id", None)),  # type: ignore
        fine_grained_feed_conflict_id=toInt(request.query_params.get("fine_grained_feed_conflict_id", None)),  # type: ignore
    )


@feed_router.get("/getAllFineGrainedFeedConflict", auth_required=True)
async def getAllFineGrainedFeedConflictRouter(request: Request):
    id = getUserIdByAccessToken(request)
    scope = request.query_params.get("scope", None)
    return getAllFineGrainedFeedConflict(
        user_id=id,
        fr_id=toInt(request.query_params.get("fr_id", None)),  # type: ignore
        scope=scope if isinstance(scope, str) else "unresolved",  # type: ignore
    )
