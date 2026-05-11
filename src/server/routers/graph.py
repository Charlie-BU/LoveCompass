import logging

from robyn import Request, Response, SubRouter
from robyn.authentication import BearerGetter

from src.agents.graphs.ConversationGraph.graph import getConversationGraph
from src.agents.graphs.FRBuildingGraph.graph import getFRBuildingGraph
from src.server.auth import AuthHandler
from src.services.user import getUserIdByAccessToken
from src.utils.index import parseInt

logger = logging.getLogger(__name__)
graph_router = SubRouter(__file__, prefix="/graph")


@graph_router.exception
def handleException(error):
    logger.error(error)
    return Response(status_code=500, description="Internal Server Error", headers={})


graph_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


@graph_router.post("/conversation", auth_required=True)
async def runConversationGraphRouter(request: Request):
    """
    调用 ConversationGraph 生成本轮回复
    """
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    messages_received = body.get("messages_received", None)
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    if not isinstance(messages_received, list) or not all(
        isinstance(item, str) for item in messages_received
    ):
        return {"status": -1, "message": "messages_received is invalid"}

    user_id = getUserIdByAccessToken(request=request)
    graph = await getConversationGraph()
    short_term_memory_config = {"configurable": {"thread_id": str(fr_id)}}
    init_state = {
        "request": {
            "user_id": user_id,
            "fr_id": fr_id,
            "messages_received": messages_received,
        },
    }
    res = await graph.ainvoke(init_state, config=short_term_memory_config)
    return {"status": 200, "message": "Run ConversationGraph success", "result": res}


@graph_router.post("/frBuilding", auth_required=True)
async def runFRBuildingGraphRouter(request: Request):
    """
    调用 FRBuildingGraph 完善人物画像
    """
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    raw_content = body.get("raw_content", "")

    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    if not isinstance(raw_content, str) or raw_content.strip() == "":
        return {"status": -1, "message": "raw_content is invalid"}

    user_id = getUserIdByAccessToken(request=request)
    init_state = {
        "request": {
            "user_id": user_id,
            "fr_id": fr_id,
            "raw_content": raw_content,
        },
    }
    try:
        async with getFRBuildingGraph() as graph:
            res = await graph.ainvoke(init_state)
    except RuntimeError as rte:
        if "FRBuildingGraph is running" in str(rte):
            return {"status": -2, "message": "FRBuildingGraph is running, please wait"}
        raise rte

    return {"status": 200, "message": "Run FRBuildingGraph success", "result": res}
