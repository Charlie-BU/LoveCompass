import logging
from robyn import Request, Response, SubRouter
from robyn.authentication import BearerGetter

from src.database.enums import (
    ConflictStatus,
    FineGrainedFeedConfidence,
    FineGrainedFeedDimension,
    OriginalSourceType,
    parseEnum,
)
from src.server.auth import AuthHandler
from src.services.fine_grained_feed import (
    addFineGrainedFeed,
    addFineGrainedFeedConflict,
    addOriginalSource,
    deleteFineGrainedFeed,
    deleteOriginalSource,
    getAllFineGrainedFeed,
    getAllFineGrainedFeedConflict,
    getAllOriginalSource,
    getFineGrainedFeed,
    getFineGrainedFeedConflict,
    getOriginalSource,
    hardDeleteFineGrainedFeedConflict,
    recallFineGrainedFeeds,
    resolveFineGrainedFeedConflict,
    updateFineGrainedFeed,
)
from src.services.user import getUserIdByAccessToken
from src.utils.index import parseInt

logger = logging.getLogger(__name__)
fine_grained_feed_router = SubRouter(__file__, prefix="/feed")


@fine_grained_feed_router.exception
def handleException(error):
    logger.error(error)
    return Response(status_code=500, description="Internal Server Error", headers={})


fine_grained_feed_router.configure_authentication(
    AuthHandler(token_getter=BearerGetter())
)


@fine_grained_feed_router.post("/addFineGrainedFeed", auth_required=True)
async def addFineGrainedFeedRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    original_source_id = parseInt(body.get("original_source_id", None))
    dimension = parseEnum(FineGrainedFeedDimension, body.get("dimension", None))
    confidence = parseEnum(FineGrainedFeedConfidence, body.get("confidence", None))
    content = body.get("content", "")
    sub_dimension = body.get("sub_dimension", None)

    if fr_id is None or original_source_id is None:
        return {"status": -1, "message": "fr_id or original_source_id is invalid"}
    if dimension is None or confidence is None or not isinstance(content, str):
        return {"status": -1, "message": "Add FineGrainedFeed args are invalid"}
    if sub_dimension is not None and not isinstance(sub_dimension, str):
        return {"status": -1, "message": "sub_dimension is invalid"}

    user_id = getUserIdByAccessToken(request=request)
    return await addFineGrainedFeed(
        user_id=user_id,
        fr_id=fr_id,
        original_source_id=original_source_id,
        dimension=dimension,
        confidence=confidence,
        content=content,
        sub_dimension=sub_dimension,
    )


@fine_grained_feed_router.post("/deleteFineGrainedFeed", auth_required=True)
async def deleteFineGrainedFeedRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    fine_grained_feed_id = parseInt(body.get("fine_grained_feed_id", None))
    if fr_id is None or fine_grained_feed_id is None:
        return {"status": -1, "message": "fr_id or fine_grained_feed_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return deleteFineGrainedFeed(
        user_id=user_id, fr_id=fr_id, fine_grained_feed_id=fine_grained_feed_id
    )


@fine_grained_feed_router.post("/updateFineGrainedFeed", auth_required=True)
async def updateFineGrainedFeedRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    fine_grained_feed_id = parseInt(body.get("fine_grained_feed_id", None))
    new_original_source_id = parseInt(body.get("new_original_source_id", None))
    new_content = body.get("new_content", "")
    new_sub_dimension = body.get("new_sub_dimension", None)

    if fr_id is None or fine_grained_feed_id is None or new_original_source_id is None:
        return {
            "status": -1,
            "message": "fr_id or fine_grained_feed_id or new_original_source_id is invalid",
        }
    if not isinstance(new_content, str):
        return {"status": -1, "message": "new_content is invalid"}
    if new_sub_dimension is not None and not isinstance(new_sub_dimension, str):
        return {"status": -1, "message": "new_sub_dimension is invalid"}

    user_id = getUserIdByAccessToken(request=request)
    return await updateFineGrainedFeed(
        user_id=user_id,
        fr_id=fr_id,
        fine_grained_feed_id=fine_grained_feed_id,
        new_original_source_id=new_original_source_id,
        new_content=new_content,
        new_sub_dimension=new_sub_dimension,
    )


@fine_grained_feed_router.get("/getFineGrainedFeed", auth_required=True)
async def getFineGrainedFeedRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    fine_grained_feed_id = parseInt(
        request.query_params.get("fine_grained_feed_id", None)
    )
    if fr_id is None or fine_grained_feed_id is None:
        return {"status": -1, "message": "fr_id or fine_grained_feed_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return getFineGrainedFeed(
        user_id=user_id, fr_id=fr_id, fine_grained_feed_id=fine_grained_feed_id
    )


@fine_grained_feed_router.get("/getAllFineGrainedFeed", auth_required=True)
async def getAllFineGrainedFeedRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return getAllFineGrainedFeed(user_id=user_id, fr_id=fr_id)


@fine_grained_feed_router.post("/recallFineGrainedFeeds", auth_required=True)
async def recallFineGrainedFeedsRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    raw_scope = body.get("scope", None)
    query = body.get("query", None)
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    if not isinstance(raw_scope, list) or not raw_scope:
        return {"status": -1, "message": "scope is invalid"}
    if query is not None and not isinstance(query, str):
        return {"status": -1, "message": "query is invalid"}

    normalized_scope = []
    for item in raw_scope:
        if not isinstance(item, dict):
            return {"status": -1, "message": "scope item is invalid"}
        scope_value = item.get("scope", None)
        top_k = parseInt(item.get("top_k", None))
        if top_k is None:
            return {"status": -1, "message": "scope item top_k is invalid"}
        if scope_value == "all":
            normalized_scope.append({"scope": "all", "top_k": top_k})
            continue
        parsed_scope = parseEnum(FineGrainedFeedDimension, scope_value)
        if parsed_scope is None:
            return {"status": -1, "message": "scope item scope is invalid"}
        normalized_scope.append({"scope": parsed_scope, "top_k": top_k})

    user_id = getUserIdByAccessToken(request=request)
    return await recallFineGrainedFeeds(
        user_id=user_id, fr_id=fr_id, scope=normalized_scope, query=query
    )


@fine_grained_feed_router.post("/addOriginalSource", auth_required=True)
async def addOriginalSourceRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    source_type = parseEnum(OriginalSourceType, body.get("type", None))
    confidence = parseEnum(FineGrainedFeedConfidence, body.get("confidence", None))
    raw_dimensions = body.get("included_dimensions", None)
    content = body.get("content", "")
    approx_date = body.get("approx_date", None)

    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    if source_type is None or confidence is None:
        return {"status": -1, "message": "type or confidence is invalid"}
    if not isinstance(raw_dimensions, list) or not raw_dimensions:
        return {"status": -1, "message": "included_dimensions is invalid"}
    if not isinstance(content, str):
        return {"status": -1, "message": "content is invalid"}
    if approx_date is not None and not isinstance(approx_date, str):
        return {"status": -1, "message": "approx_date is invalid"}

    included_dimensions = []
    for item in raw_dimensions:
        parsed_dimension = parseEnum(FineGrainedFeedDimension, item)
        if parsed_dimension is None:
            return {"status": -1, "message": "included_dimensions item is invalid"}
        included_dimensions.append(parsed_dimension)

    user_id = getUserIdByAccessToken(request=request)
    return addOriginalSource(
        user_id=user_id,
        fr_id=fr_id,
        type=source_type,
        confidence=confidence,
        included_dimensions=included_dimensions,
        content=content,
        approx_date=approx_date,
    )


@fine_grained_feed_router.post("/deleteOriginalSource", auth_required=True)
async def deleteOriginalSourceRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    original_source_id = parseInt(body.get("original_source_id", None))
    if fr_id is None or original_source_id is None:
        return {"status": -1, "message": "fr_id or original_source_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return deleteOriginalSource(
        user_id=user_id, fr_id=fr_id, original_source_id=original_source_id
    )


@fine_grained_feed_router.get("/getOriginalSource", auth_required=True)
async def getOriginalSourceRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    original_source_id = parseInt(request.query_params.get("original_source_id", None))
    if fr_id is None or original_source_id is None:
        return {"status": -1, "message": "fr_id or original_source_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return getOriginalSource(
        user_id=user_id, fr_id=fr_id, original_source_id=original_source_id
    )


@fine_grained_feed_router.get("/getAllOriginalSource", auth_required=True)
async def getAllOriginalSourceRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return getAllOriginalSource(user_id=user_id, fr_id=fr_id)


@fine_grained_feed_router.post("/addFineGrainedFeedConflict", auth_required=True)
async def addFineGrainedFeedConflictRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    dimension = parseEnum(FineGrainedFeedDimension, body.get("dimension", None))
    feed_ids_raw = body.get("feed_ids", None)
    old_value = body.get("old_value", "")
    new_value = body.get("new_value", "")
    conflict_detail = body.get("conflict_detail", "")
    status = (
        parseEnum(ConflictStatus, body.get("status", None)) or ConflictStatus.PENDING
    )

    if fr_id is None or dimension is None:
        return {"status": -1, "message": "fr_id or dimension is invalid"}
    if not isinstance(feed_ids_raw, list) or not feed_ids_raw:
        return {"status": -1, "message": "feed_ids is invalid"}
    if not isinstance(old_value, str) or not isinstance(new_value, str):
        return {"status": -1, "message": "old_value or new_value is invalid"}
    if not isinstance(conflict_detail, str):
        return {"status": -1, "message": "conflict_detail is invalid"}

    feed_ids = []
    for feed_id in feed_ids_raw:
        parsed_id = parseInt(feed_id)
        if parsed_id is None:
            return {"status": -1, "message": "feed_ids item is invalid"}
        feed_ids.append(parsed_id)

    user_id = getUserIdByAccessToken(request=request)
    return addFineGrainedFeedConflict(
        user_id=user_id,
        fr_id=fr_id,
        dimension=dimension,
        feed_ids=feed_ids,
        old_value=old_value,
        new_value=new_value,
        conflict_detail=conflict_detail,
        status=status,
    )


@fine_grained_feed_router.post("/hardDeleteFineGrainedFeedConflict", auth_required=True)
async def hardDeleteFineGrainedFeedConflictRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    conflict_id = parseInt(body.get("fine_grained_feed_conflict_id", None))
    if fr_id is None or conflict_id is None:
        return {
            "status": -1,
            "message": "fr_id or fine_grained_feed_conflict_id is invalid",
        }
    user_id = getUserIdByAccessToken(request=request)
    return hardDeleteFineGrainedFeedConflict(
        user_id=user_id, fr_id=fr_id, fine_grained_feed_conflict_id=conflict_id
    )


@fine_grained_feed_router.post("/resolveFineGrainedFeedConflict", auth_required=True)
async def resolveFineGrainedFeedConflictRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    conflict_id = parseInt(body.get("fine_grained_feed_conflict_id", None))
    status = parseEnum(ConflictStatus, body.get("status", None))
    if fr_id is None or conflict_id is None or status is None:
        return {
            "status": -1,
            "message": "fr_id or fine_grained_feed_conflict_id or status is invalid",
        }
    user_id = getUserIdByAccessToken(request=request)
    return resolveFineGrainedFeedConflict(
        user_id=user_id,
        fr_id=fr_id,
        fine_grained_feed_conflict_id=conflict_id,
        status=status,
    )


@fine_grained_feed_router.get("/getFineGrainedFeedConflict", auth_required=True)
async def getFineGrainedFeedConflictRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    conflict_id = parseInt(
        request.query_params.get("fine_grained_feed_conflict_id", None)
    )
    if fr_id is None or conflict_id is None:
        return {
            "status": -1,
            "message": "fr_id or fine_grained_feed_conflict_id is invalid",
        }
    user_id = getUserIdByAccessToken(request=request)
    return getFineGrainedFeedConflict(
        user_id=user_id, fr_id=fr_id, fine_grained_feed_conflict_id=conflict_id
    )


@fine_grained_feed_router.get("/getAllFineGrainedFeedConflict", auth_required=True)
async def getAllFineGrainedFeedConflictRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    scope = request.query_params.get("scope", None) or "unresolved"
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    if scope not in ("all", "unresolved", "resolved"):
        return {"status": -1, "message": "scope is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return getAllFineGrainedFeedConflict(user_id=user_id, fr_id=fr_id, scope=scope)
