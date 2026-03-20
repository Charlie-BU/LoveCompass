import asyncio
import dotenv
from src.agent.llm import ainvokeWithNoContext, prepareLLM

dotenv.load_dotenv()


async def testLLM():
    prompt = """
    请告诉我这两张图片分别是什么
    """
    llm = prepareLLM(model="DOUBAO_2_0_LITE", options={
        "temperature": 0.2,
        "reasoning_effort": "high",
    })
    res = await ainvokeWithNoContext(
        llm=llm,
        prompt=prompt,
        images_urls=[
            "https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/baosheng.jpeg",
            "https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/wenwen.jpeg",
        ],
    )
    print(res)


if __name__ == "__main__":
    import time
    start = time.perf_counter()
    asyncio.run(testLLM())
    print(f"cost time: {time.perf_counter() - start}")
