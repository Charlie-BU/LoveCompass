import asyncio
import json
import requests

from .react_agent import askWithNoContext, getAgent

prompt = """
请告诉我这两张图片分别是什么
"""


def testAPI():
    url = "http://localhost:1314/api/v3/bots/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,  # 启用流式响应
    }

    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=data, headers=headers, stream=True)
        response.raise_for_status()

        print("Response stream:")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data:"):
                    json_str = decoded_line[5:]
                    if json_str != "[DONE]":
                        delta = json.loads(decoded_line[5:])["choices"][0]["delta"][
                            "content"
                        ]
                        print(delta, end="")
    except Exception as e:
        print(f"Error: {e}")


async def testAgent():
    try:
        agent = await getAgent()
        res = await askWithNoContext(
            react_agent=agent,
            prompt=prompt,
            images_urls=[
                "https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/baosheng.jpeg",
                "https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/wenwen.jpeg",
            ],
        )
        print(res)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(testAgent())
