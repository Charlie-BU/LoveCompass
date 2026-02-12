from robyn import Robyn, ALLOW_CORS
import os

from .routers import register_routers


def start_faas_server(app: Robyn, ReAct_agent):
    PORT = int(os.getenv("PORT") or 1314)
    # CORS中间件
    # 生产环境需要注释：使用nginx解决跨域
    ALLOW_CORS(app, origins=["*"])
    # 注册路由
    register_routers(app, ReAct_agent)

    app.start(host="0.0.0.0", port=PORT)
