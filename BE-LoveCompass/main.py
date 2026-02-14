import asyncio
import os
from dotenv import load_dotenv
from robyn import Robyn

from agent.index import create_agent_graph
from agent.llm import prepare_llm

# from agent.mcp import get_mcp_psms_list, init_mcp_tools
from server.faas import init_faas_server


SYSTEM_PROMPT = """
你是“LoveCompass”恋爱辅助产品的智能助手。
你的目标是基于用户提供的上下文，帮助用户理解关系现状、构建对方画像、给出更合适的沟通与推进建议。
你必须使用中文回答。

核心原则：
1. 以用户提供的上下文为准，不编造事实。
2. 用MBTI作为参考，不把MBTI当作决定性结论。
3. 建议需要可执行、低风险、尊重对方边界与感受。
4. 先理解再建议，明确问题与目标后输出方案。
5. 当上下文不足时，提出高价值的补充信息请求。

输出要求：
1. 先给出简洁结论，再给出理由与可执行动作。
2. 若存在多个可行路径，给出方案对比与适用条件。
3. 提供具体话术示例时，保持自然、真实、不过度操控。
"""

load_dotenv()


async def main():
    # 1. Prepare LLM
    llm = prepare_llm()

    # 2. Prepare Tools
    # mcp_psms_list = get_mcp_psms_list()
    # tools = await init_mcp_tools(mcp_psms_list)

    # 3. Init Agent
    ReAct_agent = create_agent_graph(llm=llm, tools=[], system_prompt=SYSTEM_PROMPT)

    # 4. Prepare Server
    app = Robyn(__file__)

    await init_faas_server(app, ReAct_agent)
    return app


if __name__ == "__main__":
    app = asyncio.run(main())
    PORT = int(os.getenv("PORT") or 1314)
    app.start(host="0.0.0.0", port=PORT)
