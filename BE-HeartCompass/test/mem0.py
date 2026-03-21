import os
from mem0 import MemoryClient
import json
import time
import requests


def check_job_status(host: str, api_key: str, event_id: str):
    # 轮询任务状态直到 SUCCEEDED
    job_status = "PENDING"
    print(f"开始轮询任务状态，event_id: {event_id}")
    while job_status != "SUCCEEDED":
        try:
            # 发送请求查询任务状态
            response = requests.get(
                f"{host}/v1/job/{event_id}/",
                headers={"Authorization": f"Token {api_key}"},
            )
            if response.status_code == 200:
                job_info = response.json()
                job_status = job_info["status"]
                print(f"当前任务状态: {job_status}")
                # 如果任务已经完成，打印完整信息
                if job_status == "SUCCEEDED":
                    print(
                        f"任务已完成，完整信息: {json.dumps(job_info, ensure_ascii=False)}"
                    )
            else:
                print(f"查询任务状态失败，状态码: {response.status_code}")
            # 每秒轮询一次
            time.sleep(1)
        except Exception as e:
            print(f"轮询过程中发生错误: {str(e)}")
            time.sleep(1)
    print(f"任务{event_id}处理完成")


# 记忆库 Mem0 配置信息
api_key = os.getenv("MEM0_API_KEY")
host = os.getenv("MEM0_HOST")
m = MemoryClient(host=host, api_key=api_key)

user_id = "xiaochen1"
# messages = [
#     {"role": "assistant", "content": "你好呀！能先告诉我你叫什么名字吗？"},
#     {"role": "user", "content": "我叫李明。今年30岁了。"},
#     {
#         "role": "assistant",
#         "content": "很高兴认识你，李明！看您资料是来自北京对吧？为了能更好地为您服务，想了解一下您的饮食偏好，比如您吃辣吗？",
#     },
#     {
#         "role": "user",
#         "content": "是休闲旅游。我穿衣嘛，平时基本都穿黑色或灰色的衣服，比较喜欢简约休闲的风格，舒服最重要。",
#     },
# ]

# print("===================异步添加记忆===============================")
# ret = m.add(messages, user_id=user_id, async_mode=True)
# print(json.dumps(ret, ensure_ascii=False))
# check_job_status(host, api_key, event_id=ret["results"][0]["event_id"])

# time.sleep(5)

# print("===================获取全部记忆===============================")
# all_memories = m.get_all(user_id=user_id)
# print(json.dumps(all_memories, ensure_ascii=False))

# print("===================根据 query 召回记忆===============================")
# query = "用户的工作信息"
# relevant_memories = m.search(query, user_id=user_id)
# print(json.dumps(relevant_memories, ensure_ascii=False))

# print("===================获取每条记忆详细信息===============================")
# for item in relevant_memories["results"]:
#     memory_id = item["id"]
#     response = m.get(memory_id)
#     print(json.dumps(response, ensure_ascii=False))

# print("===================获取每条记忆历史记录===============================")
# memory_id = 0
# for item in relevant_memories["results"]:
#     memory_id = item["id"]
#     response = m.history(memory_id)
#     print(json.dumps(response, ensure_ascii=False))

# print("===================更新单条记忆===============================")
# response = m.update(memory_id, "没有结婚，是单身")
# print(json.dumps(response, ensure_ascii=False))

# print("===================删除单条记忆===============================")
# for item in relevant_memories["results"]:
#     memory_id = item["id"]
#     response = m.delete(memory_id)
#     print(json.dumps(response, ensure_ascii=False))

# print("===================删除所有记忆===============================")
# response = m.delete_all(user_id=user_id)
# print(json.dumps(response, ensure_ascii=False))

print("===================Demo执行完成===============================")
