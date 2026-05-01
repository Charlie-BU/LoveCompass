from robyn import SubRouter, Request, Response
from robyn.authentication import BearerGetter
import logging
import json

from src.server.authentication import AuthHandler
from src.services.user import getUserIdByAccessToken
from src.services.knowledge import (
    addKnowledgePiece,
    recallKnowledgePieces,
    deleteKnowledgePiece,
    getKnowledgePiece,
    getAllKnowledgePieces,
)
from src.utils.index import toInt, toFloat


logger = logging.getLogger(__name__)
knowledge_router = SubRouter(__file__, prefix="/knowledge")


@knowledge_router.exception
def handleException(error):
    logger.error(error)
    return Response(status_code=500, description="Internal Server Error", headers={})


knowledge_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


@knowledge_router.post("/addKnowledgePiece", auth_required=True)
async def addKnowledgePieceRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    return await addKnowledgePiece(
        user_id=id,
        content=body.get("content", ""),
        weight=toFloat(body.get("weight"), 0.5),
    )


@knowledge_router.post("/recallKnowledgePieces", auth_required=True)
async def recallKnowledgePiecesRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    return await recallKnowledgePieces(
        user_id=id,
        query=body.get("query", ""),
        top_k=toInt(body.get("top_k")) or 10,
    )


@knowledge_router.post("/deleteKnowledgePiece", auth_required=True)
async def deleteKnowledgePieceRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    return deleteKnowledgePiece(
        user_id=id,
        knowledge_id=toInt(body.get("knowledge_id")),  # type: ignore
    )


@knowledge_router.get("/getKnowledgePiece", auth_required=True)
async def getKnowledgePieceRouter(request: Request):
    id = getUserIdByAccessToken(request)
    return getKnowledgePiece(
        user_id=id,
        knowledge_id=toInt(request.query_params.get("knowledge_id", None)),  # type: ignore
    )


@knowledge_router.get("/getAllKnowledgePieces", auth_required=True)
async def getAllKnowledgePiecesRouter(request: Request):
    id = getUserIdByAccessToken(request)
    return getAllKnowledgePieces(user_id=id)
