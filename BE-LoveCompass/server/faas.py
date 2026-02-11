from robyn import Robyn, ALLOW_CORS
from robyn.robyn import Response
import os
from dotenv import load_dotenv

from .routers import register_routers


def start_faas_server(app: Robyn):
    load_dotenv()
    PORT = int(os.getenv("PORT") or 1314)
    # CORS中间件
    # 生产环境需要注释：使用nginx解决跨域
    ALLOW_CORS(app, origins=["*"])

    # 异常处理
    @app.exception
    def handle_exception(error):
        print(f"error msg: {error}")
        return Response(status_code=500, headers={}, description=f"error msg: {error}")

    # 注册路由
    register_routers(app)

    app.start(host="0.0.0.0", port=PORT)
