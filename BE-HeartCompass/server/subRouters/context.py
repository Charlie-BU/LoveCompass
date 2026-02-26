import json
from robyn import SubRouter
from robyn.robyn import Request, Response
from robyn.authentication import BearerGetter

from ..authentication import AuthHandler
from database.database import session
from ..services.context import (
    contextAddKnowledge,
    contextAddContextByNaturalLanguage,
)
from ..services.embedding import recallEmbedding

context_router = SubRouter(__file__, prefix="/context")


# 全局异常处理
@context_router.exception
def handleException(error):
    return Response(status_code=500, description=f"error msg: {error}", headers={})


# 鉴权中间件
context_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


# 从向量数据库召回上下文
@context_router.post("/recallContextFromEmbedding", auth_required=True)
async def recallContextFromEmbedding(request: Request):
    data = request.json()
    text = data["text"]
    top_k = data["top_k"]
    recall_from = data["recall_from"]
    if isinstance(recall_from, str):
        recall_from = [recall_from]
    elif not isinstance(recall_from, list):
        return {"status": -3, "message": "Invalid recall_from"}
    relation_chain_id = data["relation_chain_id"]

    with session() as db:
        res = await recallEmbedding(
            db=db,
            text=text,
            top_k=int(top_k),
            recall_from=recall_from,
            relation_chain_id=(int(relation_chain_id) if relation_chain_id else None),
        )
    return res


@context_router.post("/addKnowledge", auth_required=True)
async def addKnowledge(request: Request):
    data = request.json()
    content = data["content"]
    with_embedding = data["with_embedding"]
    with session() as db:
        res = await contextAddKnowledge(
            db=db,
            content=json.dumps(content) if isinstance(content, dict) else content,
            with_embedding=bool(with_embedding),
        )
    return res


@context_router.post("/addContextByNaturalLanguage", auth_required=True)
async def addContextByNaturalLanguage(request: Request):
    data = request.json()
    relation_chain_id = data["relation_chain_id"]
    content = data["content"]
    with_embedding = data["with_embedding"]
    with session() as db:
        res = await contextAddContextByNaturalLanguage(
            db=db,
            relation_chain_id=int(relation_chain_id),
            content=json.dumps(content) if isinstance(content, dict) else content,
            with_embedding=bool(with_embedding),
        )
    return res
