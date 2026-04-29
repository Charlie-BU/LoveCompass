from robyn import Robyn, Response
import logging

from src.server.subrouters.user import user_router
# from src.server.subrouters.fr import fr_router
# from src.server.subrouters.feed import feed_router
# from src.server.subrouters.knowledge import knowledge_router

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
    # app.include_router(fr_router)
    # app.include_router(feed_router)
    # app.include_router(knowledge_router)

    app.get("/ping")(lambda: "pong")
