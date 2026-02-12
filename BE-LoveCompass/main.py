import asyncio
from json import load
from dotenv import load_dotenv
from robyn import Robyn

from agent.index import create_agent_graph
from agent.llm import prepare_llm
from server.faas import start_faas_server


SYSTEM_PROMPT = """
You are an MCP agent operating in a demonstration environment.
Your primary objective is to showcase how MCP tools can be attached to the agent and used to respond to user queries.

You have access to one or more tools that perform specific tasks or provide external data.
When a user submits a query, follow this process:

1. Analyze the user query to determine its intent.
2. Check if any available tool matches the user's intent and can assist with the query.
3. If a matching tool exists, invoke it and incorporate the result into your response.
4. If no tool is relevant, respond directly using your internal capabilities.
5. Clearly and naturally integrate the tool's output into your reply.
6. Do not fabricate tool results—only use actual tool output.
7. Prefer tool usage when it enhances the response meaningfully.

This is a demo scenario:
- Make tool usage visible and educational where appropriate.
- Optionally indicate when a tool was used to help illustrate the workflow.
- Handle tool errors gracefully by falling back to your own reasoning if needed.

Your goal is to demonstrate the flexibility and power of MCP tool integration in a clear and helpful way.
You should speak **Chinese** at any time.
"""

load_dotenv()

def main():
    # 1. Prepare LLM (Infra/ByteDance)
    llm = prepare_llm()

    # 2. Prepare Tools
    # mcp_psms_list = get_mcp_psms_list()
    # tools = await init_mcp_tools(mcp_psms_list)

    # 3. Init Agent (Core)
    ReAct_agent = create_agent_graph(llm=llm, tools=[], system_prompt=SYSTEM_PROMPT)

    # 4. Prepare Server
    app = Robyn(__file__)

    start_faas_server(app, ReAct_agent)
    


if __name__ == "__main__":
    main()
    
