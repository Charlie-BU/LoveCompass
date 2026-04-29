import asyncio
import logging
import os
from dotenv import load_dotenv
from robyn import Robyn, ALLOW_CORS

from src.server.routers import registerRouters


load_dotenv()
logging.basicConfig(level=logging.INFO)


async def main() -> Robyn:
    app = Robyn(__file__)
    # CORS中间件
    # 生产环境需要注释：使用nginx解决跨域
    ALLOW_CORS(app, origins=["*"])
    # 注册路由
    await registerRouters(app)
    return app


if __name__ == "__main__":
    app = asyncio.run(main())
    PORT = int(os.getenv("PORT") or 1314)
    app.start(host="0.0.0.0", port=PORT)
