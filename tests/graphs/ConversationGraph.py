import logging
import pprint
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from src.agents.graphs.ConversationGraph.graph import getConversationGraph


messages_samples = [
    # "最近去哪啦？怎么没见到你",
    # "你不是刚从美国回来？怎么到处跑？",
    # "我意思上周不是才去美国玩？",
    # "看你发朋友圈来着",
    "今天天气不错"
]


async def main():
    fr_id = 2
    graph = await getConversationGraph()
    init_state = {
        "request": {
            "user_id": 1,
            "fr_id": fr_id,
            "messages_received": messages_samples,
        },
    }
    short_term_memory_config = {"configurable": {"thread_id": str(fr_id)}}
    result = await graph.ainvoke(init_state, config=short_term_memory_config)
    return result


if __name__ == "__main__":
    import asyncio
    import time

    start_time = time.perf_counter()
    result = asyncio.run(main())
    pprint.pprint(result, indent=2)
    print(f"Total time: {time.perf_counter() - start_time}s")
