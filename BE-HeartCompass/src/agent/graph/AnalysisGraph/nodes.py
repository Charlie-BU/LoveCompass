from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
import json
import logging
import os

from .state import AnalysisGraphState
from ...tools import useKnowledge, ToolAndItsArgsHandler, handleIfToolCall
from ...llm import prepareLLM
from ...prompt import getPrompt

logger = logging.getLogger(__name__)


async def nodeFetchSystemPromptFromScreenshots(state: AnalysisGraphState) -> dict:
    system_prompt = await getPrompt(
        # todo: 提示词修改
        os.getenv("CONVERSATION_ANALYSIS"),
    )
    return {"system_prompt": system_prompt}


async def nodeFetchSystemPromptFromNarrative(state: AnalysisGraphState) -> dict:
    system_prompt = await getPrompt(
        # todo: 提示词修改
        os.getenv("NARRATIVE_ANALYSIS"),
    )
    return {"system_prompt": system_prompt}


async def nodeCallLLM(state: AnalysisGraphState) -> dict:
    llm: ChatOpenAI = prepareLLM(model="DOUBAO_2_0_LITE")
    llm_with_tools = llm.bind_tools([useKnowledge])

    type = state["request"].get("type")
    match type:
        case "conversation":
            human_message = [
                {
                    "type": "text",
                    "text": f"补充上下文：{state['request'].get('additional_context')}\n对方在截图中为{state['request'].get('crush_name')}",
                }
            ]
            # 聊天记录分析才会有图片
            screenshot_urls = state["request"].get("conversation_screenshots")
            if screenshot_urls:
                for url in screenshot_urls:
                    if not url:
                        continue
                    human_message.append(
                        {"type": "image_url", "image_url": {"url": url}}
                    )
        case "narrative":
            human_message = [
                {"type": "text", "text": state["request"].get("narrative")}
            ]

    messages = []
    # context_block 放到System Message中
    messages.append(SystemMessage(content=state["system_prompt"]))
    messages.append(SystemMessage(content=state["context_block"]))
    messages.append(HumanMessage(content=human_message))

    response = await llm_with_tools.ainvoke(messages)
    # 处理tool call
    response = (
        await handleIfToolCall(
            tools_and_args_handlers=[
                ToolAndItsArgsHandler(
                    tool=useKnowledge,
                    args_handler=lambda _tool_call, _messages: {
                        "relation_chain_id": state["request"].get("relation_chain_id")
                    },
                )
            ],
            messages=messages,
            llm_with_tools=llm_with_tools,
            llm_response=response,
            max_tool_round=3,
        )
    )[0]

    response_content = response.content if hasattr(response, "content") else response
    parsed = None
    if isinstance(response_content, dict):
        parsed = response_content
    elif isinstance(response_content, str):
        try:
            parsed = json.loads(response_content)
        except json.JSONDecodeError:
            logger.warning(f"Error parsing LLM response: {response_content}")

    llm_output = {
        "message_candidates": [],
        "risks": [],
        "suggestions": [],
        "message": "模型输出解析失败",
    }
    if isinstance(parsed, dict):
        if parsed.get("status") == 200:
            data = parsed.get("data") or {}
            llm_output["message_candidates"] = data.get("message_candidates", []) or []
            llm_output["risks"] = data.get("risks", []) or []
            llm_output["suggestions"] = data.get("suggestions", []) or []
            llm_output["message"] = None
        else:
            llm_output["message"] = parsed.get("message") or ""

    # 把新一轮加入记忆
    messages_in_memory = state.get("messages", [])
    messages_to_update_memory = []
    non_system_messages = []
    for msg in messages_in_memory:
        if isinstance(msg, SystemMessage):
            if getattr(msg, "id", None) is not None:
                messages_to_update_memory.append(RemoveMessage(id=msg.id))
            continue
        non_system_messages.append(msg)
    messages_to_update_memory.append(SystemMessage(content=state["system_prompt"]))
    messages_to_update_memory.append(SystemMessage(content=state["context_block"]))
    messages_to_update_memory.extend(non_system_messages)
    messages_to_update_memory.append(HumanMessage(content=human_message))
    messages_to_update_memory.append(response)
    return {"llm_output": llm_output, "messages": messages_to_update_memory}
