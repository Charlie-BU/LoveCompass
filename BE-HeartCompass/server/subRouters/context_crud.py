from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from ..services.context_crud import ccDeleteEvent
from database.database import session


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
    event_id = body["id"]
    with session() as db:
        res = await ccDeleteEvent(db=db, id=int(event_id))
    return res
