# 弃用，火山Mem0支持太差
# update接口跑不通；add memory慢到令人发指的程度；v2 API不支持；文档啥也没有；oncall找不到人

#  import os
# import logging
# from functools import lru_cache
# from typing import Any, Dict, List
# from mem0 import MemoryClient

# from src.request import fetch

# logger = logging.getLogger(__name__)


# # 全局单例
# @lru_cache
# def mem0Client() -> MemoryClient:
#     api_key = os.getenv("MEM0_API_KEY")
#     host = os.getenv("MEM0_HOST")
#     assert api_key and host, "required 'MEM0_API_KEY' and 'MEM0_HOST' for AI Agent!!!"

#     client = MemoryClient(host=host, api_key=api_key)
#     return client


# async def checkJobStatus(event_id: str) -> dict:
#     url = f'{os.getenv("MEM0_HOST")}/v1/job/{event_id}'
#     try:
#         res = await fetch(
#             url,
#             headers={
#                 "Authorization": f"Token {os.getenv("MEM0_API_KEY")}",
#             },
#         )
#         if res["status_code"] != 200:
#             raise Exception(f'{res["status_code"]} {res["body"]}')
#         return res["body"]
#     except Exception as e:
#         logger.error(f"Error checking job status for event_id {event_id}: {e}")
#         return {}


# def addMemoryOnRelationChain(
#     relation_chain_id: int,
#     memory: str | List[Dict[str, str]],
# ) -> Dict[str, Any]:
#     client = mem0Client()
#     ret = client.add(memory, user_id=str(relation_chain_id), async_mode=True)
#     return ret


# def getAllMemoriesByRelationChainId(
#     relation_chain_id: int,
# ) -> Dict[str, Any]:
#     client = mem0Client()
#     all_memories = client.get_all(user_id=str(relation_chain_id))
#     return all_memories


# def recallMemories(
#     relation_chain_id: int,
#     query: str,
# ) -> Dict[str, Any]:
#     client = mem0Client()
#     memories = client.search(query=query, user_id=str(relation_chain_id))
#     return memories


# def getMemoryDetail(
#     memory_id: str,
# ) -> Dict[str, Any]:
#     client = mem0Client()
#     memory = client.get(memory_id)
#     return memory


# def getMemoryHistory(
#     memory_id: str,
# ) -> Dict[str, Any]:
#     client = mem0Client()
#     history = client.history(memory_id)
#     return history


# def updateMemory(
#     memory_id: str,
#     new_memory: str,
# ) -> Dict[str, Any]:
#     client = mem0Client()
#     res = client.update(memory_id=memory_id, text=new_memory)
#     return res


# def deleteMemory(
#     memory_id: str,
# ) -> Dict[str, Any]:
#     client = mem0Client()
#     res = client.delete(memory_id)
#     return res


# def deleteAllMemoriesByRelationChainId(
#     relation_chain_id: int,
# ) -> Dict[str, Any]:
#     client = mem0Client()
#     res = client.delete_all(user_id=str(relation_chain_id))
#     return res
