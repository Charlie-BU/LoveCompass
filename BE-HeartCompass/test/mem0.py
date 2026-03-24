import time
from src.agent.mem0 import (
    mem0Client,
    checkJobStatus,
    addMemoryOnRelationChain,
    getAllMemoriesByRelationChainId,
    recallMemories,
    getMemoryHistory,
    updateMemory,
    deleteMemory,
    deleteAllMemoriesByRelationChainId,
)


async def main():
    # res = addMemoryOnRelationChain(1, "何海涛来自福建，现在就读于同济大学")
    # print(res)
    # while True:
    #     # status = checkJobStatus(res["results"][0]["event_id"])
    #     status = await checkJobStatus("14a10a_RVOC20260324220849_mp-cnlfhdfjyr1jcylbay6pxw7uavvs")
    #     print(status)
    #     time.sleep(1)
    print(recallMemories(1, "何海涛"))


if __name__ == "__main__":
    import dotenv
    import asyncio

    dotenv.load_dotenv()

    asyncio.run(main())
