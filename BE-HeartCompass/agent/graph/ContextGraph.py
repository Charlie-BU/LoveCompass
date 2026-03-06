from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
import json
import asyncio
import logging

from database.database import session
from database.models import (
    User,
    Crush,
    RelationChain,
    ChainStageHistory,
    InteractionSignal,
)
from database.enums import RelationStage
from server.services.ai import (
    generateRecallQueriesFromScreenshots,
    generateRecallQueriesFromNarrative,
)
from server.services.embedding import recallEmbedding
from .state import (
    AllContext,
    RecallQueries,
    Request,
    Entities,
    CrushProfileContext,
    ContextGraphState,
)

logger = logging.getLogger(__name__)


# 全局单例
_context_graph_instance: CompiledStateGraph | None = None
_context_graph_lock = asyncio.Lock()


async def stepLoadEntity(request: Request) -> Entities:
    with session() as db:
        user = db.get(User, request["user_id"])
        relation_chain = db.get(RelationChain, request["relation_chain_id"])
        crush: Crush = relation_chain.crush
        stage_histories = (
            db.query(ChainStageHistory)
            .filter(ChainStageHistory.relation_chain_id == relation_chain.id)
            .order_by(ChainStageHistory.created_at.desc())
            .all()
        )
        return {
            "user": user,
            "crush": crush,
            "relation_chain": relation_chain,
            "stage_histories": stage_histories,
        }


async def stepBuildCrushProfileContext(entities: Entities) -> CrushProfileContext:
    crush = entities.get("crush")
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
        "crush_mbti": crush_mbti,
        "crush_profile": crush_profile,
    }


# 根据聊天截图和对方画像生成向量召回query
async def stepBuildRecallQueriesFromScreenshots(
    request: Request,
    entities: Entities,
    crush_profile_context: CrushProfileContext,
) -> RecallQueries:
    knowledge_query = None
    non_knowledge_query = None

    screenshot_urls = request.get("conversation_screenshots")
    additional_context = request.get("additional_context")
    profile = crush_profile_context["crush_profile"]
    is_self = (
        entities.get("relation_chain").current_stage == RelationStage.SELF
        if entities.get("relation_chain")
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
        knowledge_query = queries.get("knowledge_query")
        non_knowledge_query = queries.get("non_knowledge_query")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
    return {
        "knowledge_query": knowledge_query,
        "non_knowledge_query": non_knowledge_query,
    }


# 根据自然语言叙述和对方画像生成向量召回query
async def stepBuildRecallQueriesFromNarrative(
    request: Request,
    entities: Entities,
    crush_profile_context: CrushProfileContext,
) -> RecallQueries:
    recall_queries: RecallQueries = {
        "knowledge_query": None,
        "non_knowledge_query": None,
    }
    narrative = request.get("narrative")
    profile = crush_profile_context["crush_profile"]
    is_self = (
        entities.get("relation_chain").current_stage == RelationStage.SELF
        if entities.get("relation_chain")
        else False
    )
    try:
        queries = json.loads(
            await generateRecallQueriesFromNarrative(
                narrative=narrative,
                profile=profile,
                is_self=is_self,
            )
        )
        recall_queries["knowledge_query"] = queries.get("knowledge_query")
        recall_queries["non_knowledge_query"] = queries.get("non_knowledge_query")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
    return {
        "knowledge_query": recall_queries.get("knowledge_query"),
        "non_knowledge_query": recall_queries.get("non_knowledge_query"),
    }


async def stepRecallKnowledge(
    request: Request,
    recall_queries: RecallQueries,
) -> list:
    recalled_knowledges = []

    knowledge_query = recall_queries.get("knowledge_query")
    if knowledge_query is not None:
        with session() as db:
            res = await recallEmbedding(
                db=db,
                text=knowledge_query,
                top_k=10,
                recall_from=["knowledge"],
                relation_chain_id=request.get("relation_chain_id"),
            )
            if res["status"] == 200:
                recalled_items = res["items"]
                recalled_knowledges.extend([item["data"] for item in recalled_items])
            else:
                logger.warning(f"Error recalling knowledge items: {res}")

    return recalled_knowledges


async def stepRecallNonKnowledge(
    request: Request,
    recall_queries: RecallQueries,
) -> dict:
    events = []
    chat_topics = []
    derived_insights = []
    non_knowledge_vector_query = recall_queries.get("non_knowledge_query")
    if non_knowledge_vector_query is not None:
        with session() as db:
            res = await recallEmbedding(
                db=db,
                text=non_knowledge_vector_query,
                top_k=30,
                recall_from=["event", "chat_topic", "derived_insight"],
                relation_chain_id=request.get("relation_chain_id"),
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

    return {
        "events": events,
        "chat_topics": chat_topics,
        "derived_insights": derived_insights,
    }


async def stepGetInteractionSignal(request: Request) -> list:
    interaction_signals = []
    with session() as db:
        latest_interaction_signal = (
            db.query(InteractionSignal)
            .filter(
                InteractionSignal.relation_chain_id == request.get("relation_chain_id"),
                InteractionSignal.is_active == True,
            )
            .order_by(InteractionSignal.created_at.desc())
            .first()
        )
        if latest_interaction_signal:
            interaction_signals.append(latest_interaction_signal)

    return interaction_signals


async def stepOrganizeContext(
    entities: Entities,
    crush_profile_context: CrushProfileContext,
    all_context: AllContext,
) -> str:
    relation_chain = entities.get("relation_chain")

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

    context_block = ""
    context_block += (
        f"**当前双方关系：**{_getValue(relation_chain, 'current_stage')}\n\n"
    )
    context_block += f"**对方画像：**\n"
    context_block += f"MBTI类型：{crush_profile_context['crush_mbti']}\n"
    for key, value in crush_profile_context["crush_profile"].items():
        context_block += f"{key}：{value}\n"

    context_block += "\n"

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

    return context_block


async def node(state: ContextGraphState) -> ContextGraphState:
    request = state["request"]
    entities = await stepLoadEntity(request)
    crush_profile_context = await stepBuildCrushProfileContext(entities)

    recall_queries: RecallQueries = {
        "knowledge_query": None,
        "non_knowledge_query": None,
    }
    if request.get("narrative") and request.get("narrative") != "":
        recall_queries = await stepBuildRecallQueriesFromNarrative(
            request, entities, crush_profile_context
        )
    else:
        recall_queries = await stepBuildRecallQueriesFromScreenshots(
            request, entities, crush_profile_context
        )

    recalled_knowledges = await stepRecallKnowledge(request, recall_queries)
    recalled_non_knowledges = await stepRecallNonKnowledge(request, recall_queries)
    interaction_signals = await stepGetInteractionSignal(request)
    all_context = {
        "knowledge": recalled_knowledges,
        "event": recalled_non_knowledges["events"],
        "chat_topic": recalled_non_knowledges["chat_topics"],
        "derived_insight": recalled_non_knowledges["derived_insights"],
        "interaction_signal": interaction_signals,
    }

    context_block = await stepOrganizeContext(
        entities, crush_profile_context, all_context
    )
    return {
        "request": request,
        "context_block": context_block,
    }


async def getContextGraph() -> CompiledStateGraph:
    global _context_graph_instance
    if _context_graph_instance is not None:
        return _context_graph_instance
    async with _context_graph_lock:
        if _context_graph_instance is not None:
            return _context_graph_instance

        graph = StateGraph(
            state_schema=ContextGraphState,
            input_schema=ContextGraphState,
            output_schema=ContextGraphState,
        )
        graph.add_node("node", node)

        graph.set_entry_point("node")
        graph.add_edge("node", END)

        # ContextGraph无需短期记忆
        _context_graph_instance = graph.compile()
        return _context_graph_instance
