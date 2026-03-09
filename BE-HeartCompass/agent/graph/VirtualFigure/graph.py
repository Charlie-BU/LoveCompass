from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import json
import asyncio
import logging
import os

from .state import (
    VirtualFigureGraphState,
    VirtualFigureGraphInput,
    VirtualFigureGraphOutput,
    resetVirtualFigureGraphState,
)
from ..checkpointer import getCheckpointer
from ...llm import prepareLLM
from ...prompt import getPrompt
from database.database import session
from database.models import RelationChain
from server.services.virtual_figure import vfRecalculateContextBlock
from server.services.embedding import recallEmbedding


logger = logging.getLogger(__name__)


# 全局单例
_virtual_figure_graph_instance: CompiledStateGraph | None = None
_virtual_figure_graph_lock = asyncio.Lock()


async def nodeLoadPersona(state: VirtualFigureGraphState) -> dict:
    user_id = state["request"]["user_id"]
    relation_chain_id = state["request"]["relation_chain_id"]
    narrative = ", ".join(
        [
            item.get("message", "")
            for item in state["request"]["messages_received"]
            if isinstance(item, dict)
        ]
    )

    with session() as db:
        relation_chain = db.get(RelationChain, int(relation_chain_id))
        context_block = relation_chain.context_block
        if context_block is None or context_block == "":
            try:
                res = await vfRecalculateContextBlock(
                    user_id, relation_chain_id, narrative
                )
                context_block = res.get("context_block", "")
                if context_block is None or context_block == "":
                    logger.warning(
                        f"Error in nodeLoadPersona: fail to calculate context_block"
                    )
                    return {"memory": state["memory"]}
            except Exception as e:
                logger.warning(f"Error in nodeLoadPersona: {e}")
                return {"memory": state["memory"]}
    # 首次特判
    if state.get("memory") is None or state.get("llm_output") is None:
        state = resetVirtualFigureGraphState(state["request"])
    state["memory"]["context_block"] = context_block
    return {
        "memory": state["memory"],
        "llm_output": state["llm_output"],
    }


# todo：智能判断是否需要召回
async def nodeRecallFromDB(state: VirtualFigureGraphState) -> dict:
    relation_chain_id = state["request"]["relation_chain_id"]
    messages_received = state["request"]["messages_received"]
    messages_text = ", ".join(
        [
            item.get("message", "")
            for item in messages_received
            if isinstance(item, dict)
        ]
    )

    events = []
    chat_topics = []
    derived_insights = []
    with session() as db:
        res = await recallEmbedding(
            db=db,
            text=messages_text,
            top_k=30,
            recall_from=["event", "chat_topic", "derived_insight"],
            relation_chain_id=relation_chain_id,
        )
        if res["status"] == 200:
            recalled_items = res["items"]
            for item in recalled_items:
                match item["source"]:
                    case "event":
                        events.append(item["data"])
                    case "chat_topic":
                        chat_topics.append(item["data"])
                    case "derived_insight":
                        derived_insights.append(item["data"])
        else:
            logger.warning(f"Error recalling non-knowledge items: {res}")
            return

        recalled_facts = events + chat_topics + derived_insights

    def _getValue(item, key):
        if isinstance(item, dict):
            value = item.get(key)
        else:
            value = getattr(item, key, None)
        return value.value if hasattr(value, "value") else value  # 同时处理Enum类型

    def _formatList(value):
        if value is None:
            return ""
        if isinstance(value, list):
            return "、".join(
                [str(v) for v in value if v is not None and str(v).strip()]
            )
        return str(value)

    def _appendIfValue(label, value):
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        return f"{label}：{text}\n"

    recalled_facts = ""
    for event in events:
        content = _getValue(event, "content")
        summary = _getValue(event, "summary")
        date = _getValue(event, "date")
        outcome = _getValue(event, "outcome")
        weight = _getValue(event, "weight")
        other_info = _formatList(_getValue(event, "other_info"))

        recalled_facts += "**过往事件**：\n"
        recalled_facts += _appendIfValue("摘要", summary)
        recalled_facts += _appendIfValue("内容", content)
        recalled_facts += _appendIfValue("时间", date)
        recalled_facts += _appendIfValue("结果导向", outcome)
        recalled_facts += _appendIfValue("重要性", weight)
        recalled_facts += _appendIfValue("其他信息", other_info)
        recalled_facts += "\n"

    for chat_topic in chat_topics:
        title = _getValue(chat_topic, "title")
        summary = _getValue(chat_topic, "summary")
        content = _getValue(chat_topic, "content")
        tags = _formatList(_getValue(chat_topic, "tags"))
        participants = _formatList(_getValue(chat_topic, "participants"))
        topic_time = _getValue(chat_topic, "topic_time")
        attitude = _getValue(chat_topic, "attitude")
        weight = _getValue(chat_topic, "weight")
        other_info = _formatList(_getValue(chat_topic, "other_info"))

        recalled_facts += "**过往聊天话题**：\n"
        recalled_facts += _appendIfValue("标题", title)
        recalled_facts += _appendIfValue("摘要", summary)
        recalled_facts += _appendIfValue("内容", content)
        recalled_facts += _appendIfValue("标签", tags)
        recalled_facts += _appendIfValue("参与者", participants)
        recalled_facts += _appendIfValue("时间", topic_time)
        recalled_facts += _appendIfValue("情绪", attitude)
        recalled_facts += _appendIfValue("重要性", weight)
        recalled_facts += _appendIfValue("其他信息", other_info)
        recalled_facts += "\n"

    for derived_insight in derived_insights:
        insight = _getValue(derived_insight, "insight")
        confidence = _getValue(derived_insight, "confidence")
        weight = _getValue(derived_insight, "weight")
        additional_info = _formatList(_getValue(derived_insight, "additional_info"))

        recalled_facts += "**部分推断/洞察**：\n"
        recalled_facts += _appendIfValue("洞察", insight)
        recalled_facts += _appendIfValue("置信度", confidence)
        recalled_facts += _appendIfValue("重要性", weight)
        recalled_facts += _appendIfValue("其他信息", additional_info)
        recalled_facts += "\n"

    state["memory"]["recalled_facts_from_db"] = recalled_facts
    return {
        "memory": state["memory"],
    }


# todo
async def nodeRecallFromMem0(state: VirtualFigureGraphState) -> dict:
    state["memory"]["recalled_facts_from_mem0"] = []
    return {
        "memory": state["memory"],
    }


async def nodeBuildMessage(state: VirtualFigureGraphState) -> dict:
    messages_received_json = state["request"]["messages_received"]
    messages_received_parsed = [msg["message"] for msg in messages_received_json]
    reply_prompt = await getPrompt(
        os.getenv("VIRTUAL_FIGURE_REPLY"),
        {
            "messages_received": json.dumps(
                messages_received_parsed, ensure_ascii=False
            ),
        },
    )

    state["memory"]["messages"].append(HumanMessage(content=reply_prompt or ""))
    # todo: 调试，删
    print(f"当前短期记忆：\n{state['memory']['messages']}\n\n")
    return {
        "memory": state["memory"],
    }


async def nodeCallLLM(state: VirtualFigureGraphState) -> VirtualFigureGraphOutput:
    llm: ChatOpenAI = prepareLLM()
    messages_to_call = [
        SystemMessage(
            content=((await getPrompt(os.getenv("VIRTUAL_FIGURE_SYSTEM_PROMPT"))) or "")
        ),
        SystemMessage(
            content=f"关系与画像上下文：\n{state['memory']['context_block']}"
        ),
        SystemMessage(
            content=f"召回的长期记忆：\n{state['memory']['recalled_facts_from_db']} \n\n {json.dumps(state['memory']['recalled_facts_from_mem0'], ensure_ascii=False)}"
        ),
    ] + state["memory"]["messages"]
    response = await llm.ainvoke(messages_to_call)
    response_content = response.content if hasattr(response, "content") else response

    parsed = None
    if isinstance(response_content, dict):
        parsed = response_content
    elif isinstance(response_content, str):
        try:
            parsed = json.loads(response_content)
        except json.JSONDecodeError:
            logger.warning(f"Error parsing LLM response: {response_content}")
            parsed = None

    if parsed is None:
        logger.warning(f"Error parsing LLM response: {response_content}")
        state["llm_output"]["messages_to_send"] = []
        state["llm_output"]["thinking"] = ""
        return {
            "llm_output": state["llm_output"],
            "memory": state["memory"],
        }
    # parse成功才写入memory
    ai_message_content = (
        response_content
        if isinstance(response_content, str)
        else json.dumps(response_content, ensure_ascii=False)
    )
    state["memory"]["messages"].append(AIMessage(content=ai_message_content))

    state["llm_output"]["messages_to_send"] = parsed.get("messages_to_send", [])
    state["llm_output"]["thinking"] = parsed.get("thinking", "")
    return {
        "llm_output": state["llm_output"],
        "memory": state["memory"],
    }


async def getVirtualFigureGraph() -> CompiledStateGraph:
    global _virtual_figure_graph_instance
    if _virtual_figure_graph_instance is not None:
        return _virtual_figure_graph_instance
    async with _virtual_figure_graph_lock:
        if _virtual_figure_graph_instance is not None:
            return _virtual_figure_graph_instance

        graph = StateGraph(
            state_schema=VirtualFigureGraphState,
            input_schema=VirtualFigureGraphInput,
            output_schema=VirtualFigureGraphOutput,
        )
        graph.add_node("nodeLoadPersona", nodeLoadPersona)
        graph.add_node("nodeRecallFromDB", nodeRecallFromDB)
        graph.add_node("nodeRecallFromMem0", nodeRecallFromMem0)
        graph.add_node("nodeBuildMessage", nodeBuildMessage)
        graph.add_node("nodeCallLLM", nodeCallLLM)

        graph.set_entry_point("nodeLoadPersona")
        graph.add_edge("nodeLoadPersona", "nodeRecallFromDB")
        graph.add_edge("nodeRecallFromDB", "nodeRecallFromMem0")
        graph.add_edge("nodeRecallFromMem0", "nodeBuildMessage")
        graph.add_edge("nodeBuildMessage", "nodeCallLLM")
        graph.add_edge("nodeCallLLM", END)

        # PostgresSaver实现短期记忆
        # todo：trim
        _virtual_figure_graph_instance = graph.compile(
            checkpointer=await getCheckpointer()
        )
        return _virtual_figure_graph_instance
