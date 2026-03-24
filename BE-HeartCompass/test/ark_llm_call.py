import os
import dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.ark import arkClient
from src.agent.adapter import langchain2ArkResponsesMessages
from src.agent.llm import arkAinvoke


dotenv.load_dotenv()
# 全局单例
_ark_client = arkClient()


async def testArkChatAPI():
    resp = await _ark_client.chat.completions.create(
        model=os.getenv("DOUBAO_2_0_LITE"),
        messages=[
            {"role": "user", "content": "你好"},
        ],
    )
    print(resp)
    return resp.choices[0].message.content


async def testArkResponseAPI():
    messages_to_send = [
        SystemMessage(content=f"你叫卜天，是一个帅哥，负责用攻击性的语言与用户互动"),
        HumanMessage(
            content=[
                {"type": "input_image", "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"},
                {"type": "input_text", "text": "你看见了什么？"},
            ]
        ),
    ]
    resp = await _ark_client.responses.create(
        model=os.getenv("DOUBAO_2_0_LITE"),
        # input=[
        #     {"role": "user", "content": "我们刚刚在聊什么"},
        # ],
        input=langchain2ArkResponsesMessages(messages_to_send),
    )
    print(resp)
    return resp


async def testarkAinvoke():
    resp = await arkAinvoke(
        model="DOUBAO_2_0_LITE",
        messages=[
            SystemMessage(content=f"你叫卜天，是一个帅哥，负责用攻击性的语言与用户互动"),
            HumanMessage(content="你好"),
        ],
        model_options={
            "reasoning_effort": "minimal",
        }
    )
    print(resp)
    return resp


if __name__ == "__main__":
    import asyncio

    asyncio.run(testarkAinvoke())
