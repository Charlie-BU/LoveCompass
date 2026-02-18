from robyn.robyn import Response

from .subRouters.user import userRouter
from .subRouters.context import contextRouter
from agent.index import wrap_chat


async def register_routers(app, ReActAgent):
    # 全局异常处理
    @app.exception
    def handle_exception(error):
        return Response(status_code=500, headers={}, description=f"error msg: {error}")

    app.include_router(userRouter)
    app.include_router(contextRouter)
    app.get("/ping")(lambda: "pong")
    # chat_completions
    app.post("/api/v3/bots/chat/completions")(await wrap_chat(ReActAgent))
