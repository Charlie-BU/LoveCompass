import json
import logging
import pprint
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from src.agents.graphs.FRBuildingGraph.graph import getFRBuildingGraph


narratives = [
    "她是我母亲。1974 年 2 月生。老家是赤峰市林西县，现在住在呼和浩特。她毕业于内蒙古大学，到现在已经当了几十年的大学老师，在内蒙古工业大学教化学（她不是设计师！）。她爱打羽毛球，经常和朋友相约打羽毛球。她很瘦，几十年一直维持着 55kg 左右的体重，多年来从未变过。她很严格，这体现在从小对我的教育上。但长大后我非常欣赏和感激她对我的教育方式。她和我的 mbti 是一样的，都是 ENTJ，这意味着成功人士的可能性。",
    "她比较瘦，常年维持着类似的体重",
]

    
async def main():
    graph = getFRBuildingGraph()
    init_state = {
        "request": {
            "user_id": 1,
            "fr_id": 1,
            "raw_content": narratives[1],
            # "raw_images": [],
        },
    }
    result = await graph.ainvoke(init_state)
    return result


if __name__ == "__main__":
    import asyncio
    import time

    start_time = time.perf_counter()
    result = asyncio.run(main())
    pprint.pprint(result, indent=2)
    print(f"Total time: {time.perf_counter() - start_time}s")
