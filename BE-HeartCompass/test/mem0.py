import time
from src.agent.mem0 import (
    mem0Client,
    checkJobStatus,
    addMemoryOnRelationChain,
    getAllMemoriesByRelationChainId,
    recallMemories,
    getMemoryHistory,
    updateMemory,
    getMemoryDetail,
    deleteMemory,
    deleteAllMemoriesByRelationChainId,
)


async def main():
    # res = addMemoryOnRelationChain(1, "何海涛来自福建，现在就读于同济大学")
    # print(res)
    # while True:
    #     # status = checkJobStatus(res["results"][0]["event_id"])
    #     status = await checkJobStatus("2d953b_MVOC20260324220940_mp-cnlfhdfjyr1jcylbay6pxw7uavvs")
    #     print(status)
    #     time.sleep(1)
    print(getAllMemoriesByRelationChainId(1), end="\n\n")
    print(recallMemories(1, "何海涛"), end="\n\n")
    print(getMemoryHistory("2d953b_MVOC20260324220940_mp-cnlfhdfjyr1jcylbay6pxw7uavvs"), end="\n\n")
    # print(updateMemory("2d953b_MVOC20260324220940_mp-cnlfhdfjyr1jcylbay6pxw7uavvs", "专业是车辆工程"), end="\n\n")
    print(getMemoryDetail("2d953b_MVOC20260324220940_mp-cnlfhdfjyr1jcylbay6pxw7uavvs"), end="\n\n")


if __name__ == "__main__":
    import dotenv
    import asyncio

    dotenv.load_dotenv()

    asyncio.run(main())
