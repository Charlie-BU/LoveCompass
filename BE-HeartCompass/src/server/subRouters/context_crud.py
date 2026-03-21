from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from src.server.authentication import AuthHandler
from src.server.services.user import userGetUserIdByAccessToken
from src.server.services.context_crud import (
    ccDeleteEvent,
    ccGetEventById,
    ccGetEventsByRelationChainId,
)
from src.database.database import session


context_crud_router = SubRouter(__file__, prefix="/context")


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
