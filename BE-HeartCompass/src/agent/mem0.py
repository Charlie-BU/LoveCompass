import os
import logging
from functools import lru_cache
from mem0 import MemoryClient

from src.request import fetch

logger = logging.getLogger(__name__)


# 全局单例
@lru_cache
def arkClient():
    api_key = os.getenv("MEM0_API_KEY")
    host = os.getenv("MEM0_HOST")
    assert api_key and host, "required 'MEM0_API_KEY' and 'MEM0_HOST' for AI Agent!!!"

    client = MemoryClient(host=host, api_key=api_key)
    return client


async def checkJobStatus(event_id: str) -> dict:
    url = f"{os.getenv("MEM0_HOST")}/api/v1/job/{event_id}"
    try:
        res = await fetch(
            url,
            headers={
                "Authorization": f"Token {os.getenv("MEM0_API_KEY")}",
            },
        )
        if res.status_code != 200:
            raise Exception(f"{res.status_code} {res.text}")
        return res.body
    except Exception as e:
        logger.error(f"Error checking job status for event_id {event_id}: {e}")
        return {}


def addMemoryOnRelationChain(
    relation_chain_id: int,
    memory: str,
):
    client = arkClient()
    ret = client.add(memory, user_id=str(relation_chain_id), async_mode=True)


if __name__ == "__main__":
    import asyncio
    import dotenv

    dotenv.load_dotenv()

    async def main():
        status = await checkJobStatus("123")
        print(status)

    asyncio.run(main())
