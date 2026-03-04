# 模式2：StateGraph 工作流
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver
import json
import asyncio
import logging
import os

from database.database import session
from database.models import (
    User,
    Crush,
    RelationChain,
    ChainStageHistory,
    InteractionSignal,
)
from database.enums import RelationStage
from server.services.ai import generateRecallQueriesFromScreenshots
from server.services.embedding import recallEmbedding
from .state import LLMOutput, GraphState
from ..llm import prepareLLM
from ..prompt import getPrompt

logger = logging.getLogger(__name__)


# 全局单例
_graph_instance: CompiledStateGraph | None = None
_graph_lock = asyncio.Lock()


async def nodeLoadEntity(state: GraphState) -> dict:
    with session() as db:
        user = db.get(User, state["request"]["user_id"])
        relation_chain = db.get(RelationChain, state["request"]["relation_chain_id"])
        crush: Crush = relation_chain.crush
        stage_histories = (
            db.query(ChainStageHistory)
            .filter(ChainStageHistory.relation_chain_id == relation_chain.id)
            .order_by(ChainStageHistory.created_at.desc())
            .all()
        )
        return {
            "entities": {
                "user": user,
                "crush": crush,
                "relation_chain": relation_chain,
                "stage_histories": stage_histories,
            }
        }


async def nodeBuildCrushProfileContext(state: GraphState) -> dict:
    crush = state["entities"].get("crush")
    crush_profile = {}
    crush_mbti = None
    if crush is not None:
        crush_mbti = crush.mbti.value if crush.mbti else None

        def _setIfValue(
            key: str, value: str | list | dict | None, chinese_key: str | None = None
        ):
            if value is None:
                return
            if isinstance(value, str) and not value.strip():
                return
            if (isinstance(value, list) or isinstance(value, dict)) and len(value) == 0:
                return
            crush_profile[chinese_key or key] = value

        _setIfValue("name", crush.name, "姓名")
        _setIfValue("gender", crush.gender.value if crush.gender else None, "性别")
        _setIfValue("birthday", crush.birthday, "生日")
        _setIfValue("occupation", crush.occupation, "职业")
        _setIfValue("education", crush.education, "教育背景")
        _setIfValue("residence", crush.residence, "常住地")
        _setIfValue("hometown", crush.hometown, "家乡")
        _setIfValue("communication_style", crush.communication_style, "交流风格")
        _setIfValue("personality_tags", crush.personality_tags, "性格")
        _setIfValue("likes", crush.likes, "喜好")
        _setIfValue("dislikes", crush.dislikes, "不喜欢")
        _setIfValue("boundaries", crush.boundaries, "个人边界")
        _setIfValue("traits", crush.traits, "个人特点")
        _setIfValue("lifestyle_tags", crush.lifestyle_tags, "生活方式")
        _setIfValue("values", crush.values, "价值观")
        _setIfValue("appearance_tags", crush.appearance_tags, "外在特征")
        _setIfValue("other_info", crush.other_info, "其他信息")
    return {
        "crush_profile_context": {
            "crush_mbti": crush_mbti,
            "crush_profile": crush_profile,
        }
    }


async def nodeBuildRecallQueries(state: GraphState) -> dict:
    recall_queries = state["recall_queries"]
    screenshot_urls = state["request"].get("conversation_screenshots")
    additional_context = state["request"].get("additional_context")
    profile = state["crush_profile_context"]["crush_profile"]
    is_self = (
        state["entities"].get("relation_chain").current_stage == RelationStage.SELF
        if state["entities"].get("relation_chain")
        else False
    )
    try:
        queries = json.loads(
            await generateRecallQueriesFromScreenshots(
                screenshot_urls=screenshot_urls,
                additional_context=additional_context,
                profile=profile,
                is_self=is_self,
            )
        )
        recall_queries["knowledge_query"] = queries.get("knowledge_query")
        recall_queries["non_knowledge_query"] = queries.get("non_knowledge_query")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
    return {
        "recall_queries": recall_queries,
    }


async def nodeRecallKnowledge(state: GraphState) -> dict:
    recall_queries = state["recall_queries"]
    all_context = state["all_context"]
    knowledge_query = recall_queries.get("knowledge_query")
    if knowledge_query is not None:
        with session() as db:
            res = await recallEmbedding(
                db=db,
                text=knowledge_query,
                top_k=10,
                recall_from=["knowledge"],
                relation_chain_id=state["request"].get("relation_chain_id"),
            )
            if res["status"] == 200:
                recalled_items = res["items"]
                all_context["knowledge"] = [item["data"] for item in recalled_items]
            else:
                logger.warning(f"Error recalling knowledge items: {res}")

    return {
        "all_context": all_context,
    }


async def nodeRecallNonKnowledge(state: GraphState) -> dict:
    recall_queries = state["recall_queries"]
    all_context = state["all_context"]
    non_knowledge_vector_query = recall_queries.get("non_knowledge_query")
    if non_knowledge_vector_query is not None:
        with session() as db:
            res = await recallEmbedding(
                db=db,
                text=non_knowledge_vector_query,
                top_k=30,
                recall_from=["event", "chat_topic", "derived_insight"],
                relation_chain_id=state["request"].get("relation_chain_id"),
            )
            if res["status"] == 200:
                recalled_items = res["items"]
                for item in recalled_items:
                    match item["source"]:
                        case "event":
                            all_context["event"].append(item["data"])
                        case "chat_topic":
                            all_context["chat_topic"].append(item["data"])
                        case "derived_insight":
                            all_context["derived_insight"].append(item["data"])
            else:
                logger.warning(f"Error recalling non-knowledge items: {res}")

    return {
        "all_context": all_context,
    }


async def nodeGetInteractionSignal(state: GraphState) -> dict:
    all_context = state["all_context"]
    with session() as db:
        latest_interaction_signal = (
            db.query(InteractionSignal)
            .filter(
                InteractionSignal.relation_chain_id
                == state["request"].get("relation_chain_id"),
                InteractionSignal.is_active == True,
            )
            .order_by(InteractionSignal.created_at.desc())
            .first()
        )
        if latest_interaction_signal:
            all_context["interaction_signal"] = [latest_interaction_signal]

    return {
        "all_context": all_context,
    }


async def nodeOrganizeContext(state: GraphState) -> dict:
    crush_profile_context = state["crush_profile_context"]
    all_context = state["all_context"]
    prompt_bundle = state["prompt_bundle"]

    context_block = ""
    context_block += f"**对方画像：**\n"
    context_block += f"MBTI类型：{crush_profile_context['crush_mbti']}\n"
    for key, value in crush_profile_context["crush_profile"].items():
        context_block += f"{key}：{value}\n"

    context_block += "\n"

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

    for event in all_context["event"]:
        content = _getValue(event, "content")
        summary = _getValue(event, "summary")
        date = _getValue(event, "date")
        outcome = _getValue(event, "outcome")
        weight = _getValue(event, "weight")
        other_info = _formatList(_getValue(event, "other_info"))

        context_block += "**过往事件：**\n"
        context_block += _appendIfValue("摘要", summary)
        context_block += _appendIfValue("内容", content)
        context_block += _appendIfValue("时间", date)
        context_block += _appendIfValue("结果导向", outcome)
        context_block += _appendIfValue("重要性", weight)
        context_block += _appendIfValue("其他信息", other_info)
        context_block += "\n"

    for chat_topic in all_context["chat_topic"]:
        title = _getValue(chat_topic, "title")
        summary = _getValue(chat_topic, "summary")
        content = _getValue(chat_topic, "content")
        tags = _formatList(_getValue(chat_topic, "tags"))
        participants = _formatList(_getValue(chat_topic, "participants"))
        topic_time = _getValue(chat_topic, "topic_time")
        attitude = _getValue(chat_topic, "attitude")
        weight = _getValue(chat_topic, "weight")
        other_info = _formatList(_getValue(chat_topic, "other_info"))

        context_block += "**过往聊天话题：**\n"
        context_block += _appendIfValue("标题", title)
        context_block += _appendIfValue("摘要", summary)
        context_block += _appendIfValue("内容", content)
        context_block += _appendIfValue("标签", tags)
        context_block += _appendIfValue("参与者", participants)
        context_block += _appendIfValue("时间", topic_time)
        context_block += _appendIfValue("情绪", attitude)
        context_block += _appendIfValue("重要性", weight)
        context_block += _appendIfValue("其他信息", other_info)
        context_block += "\n"

    for derived_insight in all_context["derived_insight"]:
        insight = _getValue(derived_insight, "insight")
        confidence = _getValue(derived_insight, "confidence")
        weight = _getValue(derived_insight, "weight")
        additional_info = _formatList(_getValue(derived_insight, "additional_info"))

        context_block += "**部分推断/洞察：**\n"
        context_block += _appendIfValue("洞察", insight)
        context_block += _appendIfValue("置信度", confidence)
        context_block += _appendIfValue("重要性", weight)
        context_block += _appendIfValue("其他信息", additional_info)
        context_block += "\n"

    for interaction_signal in all_context["interaction_signal"]:
        frequency = _getValue(interaction_signal, "frequency")
        attitude = _getValue(interaction_signal, "attitude")
        window = _getValue(interaction_signal, "window")
        note = _getValue(interaction_signal, "note")
        confidence = _getValue(interaction_signal, "confidence")
        weight = _getValue(interaction_signal, "weight")
        context_block += "**互动信号：**\n"
        context_block += _appendIfValue("频率", frequency)
        context_block += _appendIfValue("态度", attitude)
        context_block += _appendIfValue("观测窗口", window)
        context_block += _appendIfValue("备注", note)
        context_block += _appendIfValue("置信度", confidence)
        context_block += _appendIfValue("重要性", weight)
        context_block += "\n"

    for knowledge in all_context["knowledge"]:
        summary = _getValue(knowledge, "summary")
        content = _getValue(knowledge, "content")
        weight = _getValue(knowledge, "weight")
        context_block += "**可能参考的相关知识：**\n"
        context_block += _appendIfValue("摘要", summary)
        context_block += _appendIfValue("内容", content)
        context_block += _appendIfValue("重要性", weight)
        context_block += "\n"

    prompt_bundle["context_block"] = context_block

    return {
        "prompt_bundle": prompt_bundle,
    }


async def nodeFetchPrompt(state: GraphState) -> dict:
    prompt_bundle = state["prompt_bundle"]

    request = state["request"]
    additional_context = request.get("additional_context") or ""
    context_block = prompt_bundle.get("context_block") or ""
    final_prompt = await getPrompt(
        os.getenv("CONVERSATION_ANALYSIS"),
        {
            "additional_context": additional_context,
            "context_block": context_block,
        },
    )
    prompt_bundle["final_prompt"] = final_prompt

    return {
        "prompt_bundle": prompt_bundle,
    }


async def nodeCallLLM(state: GraphState) -> dict:
    llm: ChatOpenAI = prepareLLM()
    screenshot_urls = state["request"].get("conversation_screenshots")
    prompt_bundle = state["prompt_bundle"]
    final_prompt = prompt_bundle.get("final_prompt") or ""

    msg = [{"type": "text", "text": final_prompt}]
    if screenshot_urls:
        for url in screenshot_urls:
            if not url:
                continue
            msg.append({"type": "image_url", "image_url": {"url": url}})

    messages = [HumanMessage(content=msg)]
    response = await llm.ainvoke(messages)
    response_content = response.content if hasattr(response, "content") else response
    parsed = None
    if isinstance(response_content, dict):
        parsed = response_content
    elif isinstance(response_content, str):
        try:
            parsed = json.loads(response_content)
        except json.JSONDecodeError:
            logger.warning(f"Error parsing LLM response: {response_content}")

    llm_output = state["llm_output"]
    if isinstance(parsed, dict):
        if parsed.get("status") == 200:
            data = parsed.get("data") or {}
            llm_output["message_candidates"] = data.get("message_candidates", []) or []
            llm_output["risks"] = data.get("risks", []) or []
            llm_output["suggestions"] = data.get("suggestions", []) or []
        else:
            llm_output["message"] = parsed.get("message") or ""

    return {
        "llm_output": llm_output,
    }


async def nodeOutput(state: GraphState) -> dict:
    llm_output = state["llm_output"]
    message_candidates = llm_output.get("message_candidates") or []
    risks = llm_output.get("risks") or []
    suggestions = llm_output.get("suggestions") or []

    return {
        "message_candidates": message_candidates,
        "risks": risks,
        "suggestions": suggestions,
    }


async def getStateGraph() -> CompiledStateGraph:
    global _graph_instance
    if _graph_instance is not None:
        return _graph_instance
    # 双检查锁模式，确保线程安全
    async with _graph_lock:
        if _graph_instance is not None:
            return _graph_instance

        graph = StateGraph(
            state_schema=GraphState, input_schema=GraphState, output_schema=LLMOutput
        )
        graph.add_node("nodeLoadEntity", nodeLoadEntity)
        graph.add_node("nodeBuildCrushProfileContext", nodeBuildCrushProfileContext)
        graph.add_node("nodeBuildRecallQueries", nodeBuildRecallQueries)
        graph.add_node("nodeRecallKnowledge", nodeRecallKnowledge)
        graph.add_node("nodeRecallNonKnowledge", nodeRecallNonKnowledge)
        graph.add_node("nodeGetInteractionSignal", nodeGetInteractionSignal)
        graph.add_node("nodeOrganizeContext", nodeOrganizeContext)
        graph.add_node("nodeFetchPrompt", nodeFetchPrompt)
        graph.add_node("nodeCallLLM", nodeCallLLM)
        graph.add_node("nodeOutput", nodeOutput)

        graph.set_entry_point("nodeLoadEntity")
        graph.add_edge("nodeLoadEntity", "nodeBuildCrushProfileContext")
        graph.add_edge("nodeBuildCrushProfileContext", "nodeBuildRecallQueries")
        graph.add_edge("nodeBuildRecallQueries", "nodeRecallKnowledge")
        graph.add_edge("nodeRecallKnowledge", "nodeRecallNonKnowledge")
        graph.add_edge("nodeRecallNonKnowledge", "nodeGetInteractionSignal")
        graph.add_edge("nodeGetInteractionSignal", "nodeOrganizeContext")
        graph.add_edge("nodeOrganizeContext", "nodeFetchPrompt")
        graph.add_edge("nodeFetchPrompt", "nodeCallLLM")
        graph.add_edge("nodeCallLLM", "nodeOutput")
        graph.add_edge("nodeOutput", END)

        # 通过 PostgresSaver 保存 checkpoint 实现短期记忆
        with PostgresSaver.from_conn_string(os.getenv("DATABASE_URI")) as checkpointer:
            _graph_instance = graph.compile(checkpointer=checkpointer)
        return _graph_instance
