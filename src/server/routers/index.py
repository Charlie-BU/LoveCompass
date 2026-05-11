from robyn import Robyn, Response
import logging

from src.server.routers.figure_and_relation import figure_and_relation_router
from src.server.routers.fine_grained_feed import fine_grained_feed_router
from src.server.routers.graph import graph_router
from src.server.routers.knowledge import knowledge_router
from src.server.routers.user import user_router

logger = logging.getLogger(__name__)


async def registerRouters(app: Robyn):
    # 全局异常处理
    @app.exception
    def handleException(error):
        logger.error(error)
        return Response(
            status_code=500, description="Internal Server Error", headers={}
        )

    app.include_router(user_router)
    app.include_router(figure_and_relation_router)
    app.include_router(fine_grained_feed_router)
    app.include_router(knowledge_router)
    app.include_router(graph_router)

    app.get("/ping")(lambda: "pong")
