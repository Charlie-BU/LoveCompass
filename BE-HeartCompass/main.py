import asyncio
import logging
import os
from dotenv import load_dotenv
from robyn import Robyn

from agent.index import getAgent
from server.faas import initFaaSServer


load_dotenv()
logging.basicConfig(level=logging.INFO)


async def main() -> Robyn:
    app = Robyn(__file__)
    ReactAgent = await getAgent()
    await initFaaSServer(app, ReactAgent)
    return app


if __name__ == "__main__":
    app = asyncio.run(main())
    PORT = int(os.getenv("PORT") or 1314)
    app.start(host="0.0.0.0", port=PORT)
