from robyn import Robyn, ALLOW_CORS

from .routers import register_routers


async def init_faas_server(app: Robyn, ReActAgent):
    # CORS中间件
    # 生产环境需要注释：使用nginx解决跨域
    ALLOW_CORS(app, origins=["*"])
    # 注册路由
    await register_routers(app, ReActAgent)
