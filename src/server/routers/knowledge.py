import logging
from robyn import Request, Response, SubRouter
from robyn.authentication import BearerGetter

from src.server.auth import AuthHandler
from src.services.knowledge import (
    addKnowledgePiece,
    deleteKnowledgePiece,
    getAllKnowledgePieces,
    getKnowledgePiece,
    recallKnowledgePieces,
)
from src.services.user import getUserIdByAccessToken
from src.utils.index import parseFloat, parseInt

logger = logging.getLogger(__name__)
knowledge_router = SubRouter(__file__, prefix="/knowledge")


@knowledge_router.exception
def handleException(error):
    logger.error(error)
    return Response(status_code=500, description="Internal Server Error", headers={})


knowledge_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


@knowledge_router.post("/addKnowledgePiece", auth_required=True)
async def addKnowledgePieceRouter(request: Request):
    body = request.json()
    content = body.get("content", "")
    weight = body.get("weight", 0.5)
    parsed_weight = parseFloat(weight)
    if not isinstance(content, str):
        return {"status": -1, "message": "content is invalid"}
    if parsed_weight is None:
        return {"status": -1, "message": "weight is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return await addKnowledgePiece(
        user_id=user_id, content=content, weight=parsed_weight
    )


@knowledge_router.get("/recallKnowledgePieces", auth_required=True)
async def recallKnowledgePiecesRouter(request: Request):
    query = request.query_params.get("query", None)
    top_k = parseInt(request.query_params.get("top_k", None) or 10)
    if not isinstance(query, str):
        return {"status": -1, "message": "query is invalid"}
    if top_k is None:
        return {"status": -1, "message": "top_k is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return await recallKnowledgePieces(user_id=user_id, query=query, top_k=top_k)


@knowledge_router.post("/deleteKnowledgePiece", auth_required=True)
async def deleteKnowledgePieceRouter(request: Request):
    body = request.json()
    knowledge_id = parseInt(body.get("knowledge_id", None))
    if knowledge_id is None:
        return {"status": -1, "message": "knowledge_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return deleteKnowledgePiece(user_id=user_id, knowledge_id=knowledge_id)


@knowledge_router.get("/getKnowledgePiece", auth_required=True)
async def getKnowledgePieceRouter(request: Request):
    knowledge_id = parseInt(request.query_params.get("knowledge_id", None))
    if knowledge_id is None:
        return {"status": -1, "message": "knowledge_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return getKnowledgePiece(user_id=user_id, knowledge_id=knowledge_id)


@knowledge_router.get("/getAllKnowledgePieces", auth_required=True)
async def getAllKnowledgePiecesRouter(request: Request):
    user_id = getUserIdByAccessToken(request=request)
    return getAllKnowledgePieces(user_id=user_id)
