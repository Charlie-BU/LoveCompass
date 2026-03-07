from robyn.robyn import Response

from .subRouters.user import user_router
from .subRouters.context import context_router
from .subRouters.analysis import analysis_router
from .subRouters.context_crud import context_crud_router
from .subRouters.virtual_figure import virtual_figure_router
from agent.react_agent import wrapChat


async def registerRouters(app, react_agent):
    # 全局异常处理
    @app.exception
    def handleException(error):
        return Response(status_code=500, headers={}, description=f"error msg: {error}")

    app.include_router(user_router)
    app.include_router(context_router)
    app.include_router(analysis_router)
    app.include_router(context_crud_router)
    app.include_router(virtual_figure_router)

    app.get("/ping")(lambda: "pong")
    # chat_completions
    app.post("/api/v3/bots/chat/completions")(await wrapChat(react_agent))
