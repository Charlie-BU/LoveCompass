import os

from main import main


async def handler():
    app = await main()
    PORT = int(os.getenv("PORT") or 1314)
    app.start(host="0.0.0.0", port=PORT)
