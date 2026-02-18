import json
from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from database.database import session
from ..services.context import contextAddKnowledge, contextCreateContext

contextRouter = SubRouter(__file__, prefix="/context")


# 全局异常处理
@contextRouter.exception
def handle_exception(error):
    return Response(status_code=500, description=f"error msg: {error}", headers={})


# 鉴权中间件
contextRouter.configure_authentication(AuthHandler(token_getter=BearerGetter()))


@contextRouter.post("/addKnowledge", auth_required=True)
async def addKnowledge(request: Request):
    data = request.json()
    content = data["content"]
    weight = data.get("weight", "1.0")
    with_embedding = data["with_embedding"]
    with session() as db:
        res = await contextAddKnowledge(
            db=db,
            content=json.dumps(content) if isinstance(content, dict) else content,
            weight=float(weight),
            with_embedding=bool(with_embedding),
        )
    return res


# todo: 建议按type拆分，不同类型上下文收集应当采用不同api
@contextRouter.post("/createContext", auth_required=True)
async def createContext(request: Request):
    data = request.json()
    relation_chain_id = data["relation_chain_id"]
    context_type = data["type"]
    content = data["content"]
    source = data["source"]

    summary = data.get("summary")
    weight = data.get("weight", "1.0")
    confidence = data.get("confidence", "1.0")
    with_embedding = data["with_embedding"]
    with session() as db:
        res = contextCreateContext(
            db=db,
            relation_chain_id=int(relation_chain_id),
            type=context_type,
            content=content,
            summary=summary,
            source=source,
            weight=float(weight),
            confidence=float(confidence),
            with_embedding=bool(with_embedding),
        )
    return res
