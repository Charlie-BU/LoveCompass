import json
import logging


from .state import ContextGraphState
from ..utils import getValueFromEntity, formatList, appendLabelIfValue
from database.database import session
from database.models import (
    RelationChain,
    InteractionSignal,
    Knowledge,
)
from database.enums import RelationStage
from server.services.ai import (
    generateRecallQueriesFromScreenshots,
    generateRecallQueriesFromNarrative,
)
from server.services.embedding import recallEmbeddingFromDB



logger = logging.getLogger(__name__)


# 生成关系与画像
async def nodeGenBasicContext(state: ContextGraphState) -> dict:
    """Generate basic context for the graph"""
    request = state["request"]
    his_mbti = None
    his_profile = {}
    current_stage = None

    crush = None
    with session() as db:
        relation_chain = db.get(RelationChain, request["relation_chain_id"])
        current_stage = relation_chain.current_stage
        crush = relation_chain.crush
    if crush is None:
        return {
            "basic_context": {
                "his_mbti": None,
                "his_profile": {},
                "current_stage": current_stage.value if current_stage else None,
            }
        }

    his_mbti = crush.mbti.value if crush.mbti else None

    def _setIfValue(
        key: str, value: str | list | dict | None, chinese_key: str | None = None
    ) -> None:
        if value is None:
            return
        if isinstance(value, str) and not value.strip():
            return
        if (isinstance(value, list) or isinstance(value, dict)) and len(value) == 0:
            return
        his_profile[chinese_key or key] = value

    _setIfValue("name", crush.name, "姓名")
    _setIfValue("gender", crush.gender.value if crush.gender else None, "性别")
    _setIfValue("birthday", crush.birthday, "生日")
    _setIfValue("occupation", crush.occupation, "职业")
    _setIfValue("education", crush.education, "教育背景")
    _setIfValue("residence", crush.residence, "常住地")
    _setIfValue("hometown", crush.hometown, "家乡")
    _setIfValue("communication_style", crush.communication_style, "交流风格")
    _setIfValue("likes", crush.likes, "喜好")
    _setIfValue("dislikes", crush.dislikes, "不喜欢")
    _setIfValue("boundaries", crush.boundaries, "个人边界")
    _setIfValue("traits", crush.traits, "个人特点")
    _setIfValue("lifestyle_tags", crush.lifestyle_tags, "生活方式")
    _setIfValue("values", crush.values, "价值观")
    _setIfValue("appearance_tags", crush.appearance_tags, "外在特征")
    _setIfValue("words_to_user", crush.words_to_user)  # 无需更换为中文键名
    _setIfValue("words_from_user", crush.words_from_user)  # 无需更换为中文键名
    _setIfValue("other_info", crush.other_info, "其他信息")

    return {
        "basic_context": {
            "his_mbti": his_mbti,
            "his_profile": his_profile,
            "current_stage": current_stage.value if current_stage else None,
        }
    }


# 根据聊天截图和对方画像生成向量召回query
async def nodeBuildRecallQueryFromScreenshots(
    state: ContextGraphState
) -> dict:
    recall_query = None

    screenshot_urls = state["request"].get("conversation_screenshots")
    crush_name = state["request"].get("crush_name")
    additional_context = state["request"].get("additional_context")

    if not screenshot_urls or not crush_name:
        return {
            "recall_query": None,
        }

    try:
        res = json.loads(
            await generateRecallQueriesFromScreenshots(
                screenshot_urls=screenshot_urls,
                crush_name=crush_name,
                additional_context=additional_context,
            )
        )
        recall_query = res.get("query")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")

    return {
        "recall_query": recall_query,
    }


# 根据自然语言叙述和对方画像生成向量召回query
async def nodeBuildRecallQueriesFromNarrative(
    state: ContextGraphState
) -> dict:
    recall_query = None

    narrative = state["request"].get("narrative")
    if not narrative:
        return {
            "recall_query": None,
        }

    try:
        res = json.loads(
            await generateRecallQueriesFromNarrative(
                narrative=narrative,
            )
        )
        recall_query = res.get("query")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")

    return {
        "recall_query": recall_query,
    }


# 从数据库召回Event、ChatTopic、DerivedInsight
async def nodeRecallFromDB(
    state: ContextGraphState,
) -> dict:
    events = []
    chat_topics = []
    derived_insights = []

    relation_chain_id = state["request"].get("relation_chain_id")
    query = state["recall_query"]

    if query is None:
        return {
            "recalled_items": {
                "events": [],
                "chat_topics": [],
                "derived_insights": [],
            }
        }

    with session() as db:
        res = await recallEmbeddingFromDB(
            db=db,
            text=query,
            top_k=30,
            recall_from=["event", "chat_topic", "derived_insight"],
            relation_chain_id=relation_chain_id,
        )
        if res["status"] == 200:
            recalled_items = res["items"]
            for item in recalled_items:
                match item["source"]:
                    case "from_event":
                        events.append(item["data"])
                    case "from_chat_topic":
                        chat_topics.append(item["data"])
                    case "from_derived_insight":
                        derived_insights.append(item["data"])
        else:
            logger.warning(f"Error recalling non-knowledge items: {res}")

    return {
        "recalled_items": {
            "events": events,
            "chat_topics": chat_topics,
            "derived_insights": derived_insights,
        }
    }


# 关键字召回MBTI相关知识
async def nodeGetMBTIKnowledge(
    state: ContextGraphState,
) -> list:
    mbti_knowledges = []

    # 通过mbti关键字召回相关知识，不使用向量召回
    mbti = state["basic_context"].get("his_mbti")
    if mbti is None:
        return {
            "mbti_knowledges": [],
        }

    with session() as db:
        knowledges_for_this_mbti = (
            db.query(Knowledge)
            .filter(Knowledge.summary.like(f"%{mbti.upper()}%"))
            .order_by(Knowledge.weight.desc())
            .all()
        )
        mbti_knowledges.extend(knowledges_for_this_mbti)
    
    # 不使用向量召回知识
    # knowledge_query = recall_queries.get("knowledge_query")
    # if knowledge_query is not None:
    #     with session() as db:
    #         res = await recallEmbeddingFromDB(
    #             db=db,
    #             text=knowledge_query,
    #             top_k=10,
    #             recall_from=["knowledge"],
    #             relation_chain_id=request.get("relation_chain_id"),
    #         )
    #         if res["status"] == 200:
    #             recalled_items = res["items"]
    #             mbti_knowledges.extend([item["data"] for item in recalled_items])
    #         else:
    #             logger.warning(f"Error recalling knowledge items: {res}")

    return {
        "mbti_knowledges": mbti_knowledges,
    }


async def nodeGetInteractionSignal(
    state: ContextGraphState,
) -> list:
    interaction_signals = []
    with session() as db:
        latest_interaction_signal = (
            db.query(InteractionSignal)
            .filter(
                InteractionSignal.relation_chain_id == state["request"].get("relation_chain_id"),
                InteractionSignal.is_active == True,
            )
            .order_by(InteractionSignal.created_at.desc())
            .first()
        )
        if latest_interaction_signal:
            interaction_signals.append(latest_interaction_signal)

    return {
        "interaction_signals": interaction_signals,
    }




async def nodeOrganizeContext(
    state: ContextGraphState,
) -> str:
    basic_context = state["basic_context"]
    recall_items = state["recalled_items"]
    mbti_knowledges = state["mbti_knowledges"]
    interaction_signals = state["interaction_signals"]

    for_virtual_figure = state["request"].get("for_virtual_figure", False)

    context_block = ""
    context_block += appendLabelIfValue("**当前双方关系**：", basic_context.get("current_stage"))

    context_block += appendLabelIfValue("**重要！** **节选对方对用户的交谈风格**：", basic_context["his_profile"].get("words_to_user"))
    if not for_virtual_figure:  # 非虚拟人物才需要节选用户对对方的交谈风格
        context_block += appendLabelIfValue("**重要！** **节选用户对对方的交谈风格**：", basic_context["his_profile"].get("words_from_user"))
    
    context_block += f"**对方画像**：\n"
    for key, value in basic_context["his_profile"].items():
        if key in ["words_to_user", "words_from_user"]:
            continue
        context_block += f"{key}：{value}\n"

    context_block += "\n"

    if len(events := recall_items["events"]) > 0:
        context_block += "**可能参考的过往事件**：\n"
        for idx, event in enumerate(events):
            content = getValueFromEntity(event, "content")
            summary = getValueFromEntity(event, "summary")
            date = getValueFromEntity(event, "date")
            outcome = getValueFromEntity(event, "outcome")
            weight = getValueFromEntity(event, "weight")
            other_info = formatList(getValueFromEntity(event, "other_info"))

            context_block += f"事件{idx+1}：\n"
            # context_block += appendLabelIfValue("摘要", summary)
            context_block += appendLabelIfValue("内容", content)
            context_block += appendLabelIfValue("时间", date)
            context_block += appendLabelIfValue("结果导向", outcome)
            # context_block += appendLabelIfValue("重要性", weight)
            context_block += appendLabelIfValue("其他信息", other_info)
            context_block += "\n"


    if len(chat_topics := recall_items["chat_topics"]) > 0:
        context_block += "**可能参考的过往聊天话题**：\n"
        for idx, chat_topic in enumerate(chat_topics):
            title = getValueFromEntity(chat_topic, "title")
            summary = getValueFromEntity(chat_topic, "summary")
            content = getValueFromEntity(chat_topic, "content")
            tags = formatList(getValueFromEntity(chat_topic, "tags"))
            participants = formatList(getValueFromEntity(chat_topic, "participants"))
            topic_time = getValueFromEntity(chat_topic, "topic_time")
            attitude = getValueFromEntity(chat_topic, "attitude")
            weight = getValueFromEntity(chat_topic, "weight")
            other_info = formatList(getValueFromEntity(chat_topic, "other_info"))

            context_block += f"聊天话题{idx+1}：\n"
            context_block += appendLabelIfValue("标题", title)
            # context_block += appendLabelIfValue("摘要", summary)
            context_block += appendLabelIfValue("内容", content)
            # context_block += appendLabelIfValue("标签", tags)
            # context_block += appendLabelIfValue("参与者", participants)
            context_block += appendLabelIfValue("时间", topic_time)
            context_block += appendLabelIfValue("情绪", attitude)
            # context_block += appendLabelIfValue("重要性", weight)
            context_block += appendLabelIfValue("其他信息", other_info)
            context_block += "\n"


    if len(derived_insights := recall_items["derived_insights"]) > 0:
        context_block += "**可能参考的推断/洞察**：\n"
        for idx, derived_insight in enumerate(derived_insights):
            insight = getValueFromEntity(derived_insight, "insight")
            confidence = getValueFromEntity(derived_insight, "confidence")
            weight = getValueFromEntity(derived_insight, "weight")
            additional_info = formatList(getValueFromEntity(derived_insight, "additional_info"))

            context_block += f"推断/洞察{idx+1}：\n"
            context_block += appendLabelIfValue("洞察", insight)
            # context_block += appendLabelIfValue("置信度", confidence)
            # context_block += appendLabelIfValue("重要性", weight)
            context_block += appendLabelIfValue("其他信息", additional_info)
            context_block += "\n"


    if len(interaction_signals := recall_items["interaction_signals"]) > 0:
        context_block += "**可能参考的互动信号**：\n"
        for idx, interaction_signal in enumerate(interaction_signals):
            frequency = getValueFromEntity(interaction_signal, "frequency")
            attitude = getValueFromEntity(interaction_signal, "attitude")
            window = getValueFromEntity(interaction_signal, "window")
            note = getValueFromEntity(interaction_signal, "note")
            confidence = getValueFromEntity(interaction_signal, "confidence")
            weight = getValueFromEntity(interaction_signal, "weight")

            context_block += f"互动信号{idx+1}：\n"
            context_block += appendLabelIfValue("频率", frequency)
            context_block += appendLabelIfValue("态度", attitude)
            context_block += appendLabelIfValue("观测窗口", window)
            context_block += appendLabelIfValue("备注", note)
            context_block += appendLabelIfValue("置信度", confidence)
            context_block += appendLabelIfValue("重要性", weight)
            context_block += "\n"


    context_block += f"对方MBTI类型：{basic_context.get('his_mbti')}\n"
    if len(mbti_knowledges := recall_items["mbti_knowledges"]) > 0:
        context_block += "**可能参考的MBTI相关知识**：\n"
        for idx, knowledge in enumerate(mbti_knowledges):
            summary = getValueFromEntity(knowledge, "summary")
            content = getValueFromEntity(knowledge, "content")
            weight = getValueFromEntity(knowledge, "weight")

            context_block += f"知识{idx+1}：\n"
            context_block += appendLabelIfValue("摘要", summary)
            context_block += appendLabelIfValue("内容", content)
            context_block += "\n"

    return {
        "context_block": context_block,
    }
