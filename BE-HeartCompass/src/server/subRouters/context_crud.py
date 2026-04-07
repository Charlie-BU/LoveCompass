from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from src.server.authentication import AuthHandler
from src.server.services.user import userGetUserIdByAccessToken
from src.server.services.context_crud import (
    ccDeleteEvent,
    ccGetEventById,
    ccGetEventsByRelationChainId,
    ccCreateCrush,
    ccCreateRelationChain,
    ccDeleteCrush,
    ccDeleteRelationChain,
    ccGetCrushById,
    ccGetCrushByUser,
    ccGetRelationChainById,
    ccGetRelationChainByUser,
    ccUpdateCrush,
)
from src.database.database import session
from src.database.enums import UserGender, RelationStage, MBTI


context_crud_router = SubRouter(__file__, prefix="/context-crud")


# 全局异常处理
@context_crud_router.exception
def handleException(error):
    return Response(status_code=500, description=f"error msg: {error}", headers={})


# 鉴权中间件
context_crud_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


@context_crud_router.post("/deleteEvent", auth_required=True)
async def deleteEvent(request: Request):
    body = request.json()
    user_id = userGetUserIdByAccessToken(request)
    event_id = body["id"]
    with session() as db:
        res = await ccDeleteEvent(db=db, user_id=user_id, event_id=int(event_id))
    return res


@context_crud_router.get("/getEventById", auth_required=True)
async def getEventById(request: Request):
    user_id = userGetUserIdByAccessToken(request)
    event_id = request.query_params.get("id", None)
    with session() as db:
        res = await ccGetEventById(db=db, user_id=user_id, event_id=int(event_id))
    return res


@context_crud_router.get("/getEventsByRelationChainId", auth_required=True)
async def getEventsByRelationChainId(request: Request):
    user_id = userGetUserIdByAccessToken(request)
    relation_chain_id = request.query_params.get("id", None)
    page_size = request.query_params.get("page_size", "10")
    current_page = request.query_params.get("current_page", "1")
    with session() as db:
        res = await ccGetEventsByRelationChainId(
            db=db,
            user_id=user_id,
            relation_chain_id=int(relation_chain_id),
            page_size=int(page_size),
            current_page=int(current_page),
        )
    return res


@context_crud_router.post("/createCrush", auth_required=True)
async def createCrush(request: Request):
    body = request.json()
    user_id = userGetUserIdByAccessToken(request)
    crush_name = body["name"]
    gender = UserGender(body["gender"])
    mbti = MBTI(body["mbti"])

    with session() as db:
        res = await ccCreateCrush(
            db=db,
            user_id=user_id,
            crush_name=crush_name,
            gender=gender,
            mbti=mbti,
        )
        return res


@context_crud_router.post("/createRelationChain", auth_required=True)
async def createRelationChain(request: Request):
    body = request.json()
    user_id = userGetUserIdByAccessToken(request)
    crush_id = body["crush_id"]
    stage = RelationStage(body["stage"])
    with session() as db:
        res = await ccCreateRelationChain(
            db=db,
            user_id=user_id,
            crush_id=crush_id,
            stage=stage,
        )
        return res


@context_crud_router.post("/deleteCrush", auth_required=True)
async def deleteCrush(request: Request):
    body = request.json()
    user_id = userGetUserIdByAccessToken(request)
    crush_id = body["crush_id"]
    with session() as db:
        res = await ccDeleteCrush(db=db, user_id=user_id, crush_id=crush_id)
        return res


@context_crud_router.post("/deleteRelationChain", auth_required=True)
async def deleteRelationChain(request: Request):
    body = request.json()
    user_id = userGetUserIdByAccessToken(request)
    relation_chain_id = body["relation_chain_id"]
    with session() as db:
        res = await ccDeleteRelationChain(
            db=db, user_id=user_id, relation_chain_id=relation_chain_id
        )
        return res


@context_crud_router.get("/getCrushById", auth_required=True)
async def getCrushById(request: Request):
    user_id = userGetUserIdByAccessToken(request)
    crush_id = request.query_params.get("crush_id", None)
    with session() as db:
        res = await ccGetCrushById(db=db, user_id=user_id, crush_id=int(crush_id))
        return res


@context_crud_router.get("/getCrushByUser", auth_required=True)
async def getCrushByUser(request: Request):
    user_id = userGetUserIdByAccessToken(request)
    page_size = request.query_params.get("page_size", "10")
    current_page = request.query_params.get("current_page", "1")
    with session() as db:
        res = await ccGetCrushByUser(
            db=db,
            user_id=user_id,
            page_size=int(page_size),
            current_page=int(current_page),
        )
        return res


@context_crud_router.get("/getRelationChainById", auth_required=True)
async def getRelationChainById(request: Request):
    user_id = userGetUserIdByAccessToken(request)
    relation_chain_id = request.query_params.get("id", None)
    with session() as db:
        res = await ccGetRelationChainById(
            db=db, user_id=user_id, relation_chain_id=int(relation_chain_id)
        )
        return res


@context_crud_router.get("/getRelationChainByUser", auth_required=True)
async def getRelationChainByUser(request: Request):
    user_id = userGetUserIdByAccessToken(request)
    page_size = request.query_params.get("page_size", "10")
    current_page = request.query_params.get("current_page", "1")
    with session() as db:
        res = await ccGetRelationChainByUser(
            db=db,
            user_id=user_id,
            page_size=int(page_size),
            current_page=int(current_page),
        )
        return res


@context_crud_router.post("/updateCrush", auth_required=True)
async def updateCrush(request: Request):
    body = request.json()
    user_id = userGetUserIdByAccessToken(request)
    crush_id = body["crush_id"]
    with session() as db:
        res = await ccUpdateCrush(db=db, user_id=user_id, crush_id=crush_id, body=body)
        return res
