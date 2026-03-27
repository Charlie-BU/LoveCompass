from langchain_core.messages import SystemMessage, HumanMessage
from datetime import datetime
import json
import logging
import os

from src.agent.graph.VirtualFigureGraph.state import (
    VirtualFigureGraphState,
    VirtualFigureGraphOutput,
)
from src.agent.llm import arkAinvoke
from src.agent.prompt import getPrompt
from src.agent.graph.utils import getValueFromEntity, formatList, appendLabelIfValue
from src.database.database import session
from src.database.models import RelationChain
from src.server.services.virtual_figure import vfRecalculateContextBlock
from src.server.services.embedding import recallEmbeddingFromDB


logger = logging.getLogger(__name__)


async def nodeInitState(state: VirtualFigureGraphState) -> dict:
    logger.info("nodeInitState is called")

    messages = state.get("messages", [])
    context_block = state.get("context_block", "")
    words_to_user = state.get("words_to_user", "")
    recalled_facts_from_db = state.get("recalled_facts_from_db", "")
    recalled_facts_from_viking = state.get("recalled_facts_from_viking", [])
    llm_output = state.get(
        "llm_output",
        {"messages_to_send": [], "reasoning_content": ""},
    )
    return {
        "messages": messages,
        "context_block": context_block,
        "words_to_user": words_to_user,
        "recalled_facts_from_db": recalled_facts_from_db,
        "recalled_facts_from_viking": recalled_facts_from_viking,
        "llm_output": llm_output,
    }


async def nodeLoadPersona(state: VirtualFigureGraphState) -> dict:
    logger.info("nodeLoadPersona is called")

    user_id = state["request"]["user_id"]
    relation_chain_id = state["request"]["relation_chain_id"]

    with session() as db:
        relation_chain = db.get(RelationChain, int(relation_chain_id))
        context_block = relation_chain.context_block
        if context_block is None or context_block == "":
            # 若当前关系链无context_block，先计算后写入
            try:
                res = await vfRecalculateContextBlock(
                    user_id,
                    relation_chain_id,
                    None,  # narrative 留空，只计算关系与画像上下文，避免重复召回相关事件、聊天话题等
                )
                context_block = res.get("context_block", "")
                if context_block is None or context_block == "":
                    logger.warning(
                        f"Error in nodeLoadPersona: fail to calculate context_block"
                    )
                    raise Exception("fail to calculate context_block")
            except Exception as e:
                logger.warning(f"Error in nodeLoadPersona: {e}")
                return {"context_block": ""}

        crush = relation_chain.crush
        state["words_to_user"] = ", ".join(crush.words_to_user)
    state["context_block"] = context_block

    return {
        "context_block": context_block,
        "words_to_user": state["words_to_user"],
    }


async def nodeRecallFromDB(state: VirtualFigureGraphState) -> dict:
    logger.info("nodeRecallFromDB is called")

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
        res = await recallEmbeddingFromDB(
            db=db,
            text=messages_text,
            top_k=20,  # todo：TBD
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
            return {"recalled_facts_from_db": ""}

    recalled_facts = ""
    for event in events:
        content = getValueFromEntity(event, "content")
        summary = getValueFromEntity(event, "summary")
        date = getValueFromEntity(event, "date")
        outcome = getValueFromEntity(event, "outcome")
        weight = getValueFromEntity(event, "weight")
        other_info = formatList(getValueFromEntity(event, "other_info"))

        recalled_facts += "**可能参考的过往事件**：\n"
        # recalled_facts += appendLabelIfValue("摘要", summary)
        recalled_facts += appendLabelIfValue("内容", content)
        recalled_facts += appendLabelIfValue("时间", date)
        recalled_facts += appendLabelIfValue("结果导向", outcome)
        # recalled_facts += appendLabelIfValue("重要性", weight)
        recalled_facts += appendLabelIfValue("其他信息", other_info)
        recalled_facts += "\n"

    for chat_topic in chat_topics:
        title = getValueFromEntity(chat_topic, "title")
        summary = getValueFromEntity(chat_topic, "summary")
        content = getValueFromEntity(chat_topic, "content")
        tags = formatList(getValueFromEntity(chat_topic, "tags"))
        participants = formatList(getValueFromEntity(chat_topic, "participants"))
        topic_time = getValueFromEntity(chat_topic, "topic_time")
        attitude = getValueFromEntity(chat_topic, "attitude")
        weight = getValueFromEntity(chat_topic, "weight")
        other_info = formatList(getValueFromEntity(chat_topic, "other_info"))

        recalled_facts += "**可能参考的过往聊天话题**：\n"
        recalled_facts += appendLabelIfValue("标题", title)
        # recalled_facts += appendLabelIfValue("摘要", summary)
        recalled_facts += appendLabelIfValue("内容", content)
        # recalled_facts += appendLabelIfValue("标签", tags)
        # recalled_facts += appendLabelIfValue("参与者", participants)
        recalled_facts += appendLabelIfValue("时间", topic_time)
        recalled_facts += appendLabelIfValue("情绪", attitude)
        # recalled_facts += appendLabelIfValue("重要性", weight)
        recalled_facts += appendLabelIfValue("其他信息", other_info)
        recalled_facts += "\n"

    for derived_insight in derived_insights:
        insight = getValueFromEntity(derived_insight, "insight")
        confidence = getValueFromEntity(derived_insight, "confidence")
        weight = getValueFromEntity(derived_insight, "weight")
        additional_info = formatList(
            getValueFromEntity(derived_insight, "additional_info")
        )

        recalled_facts += "**可能参考的推断/洞察**：\n"
        recalled_facts += appendLabelIfValue("洞察", insight)
        # recalled_facts += appendLabelIfValue("置信度", confidence)
        # recalled_facts += appendLabelIfValue("重要性", weight)
        recalled_facts += appendLabelIfValue("其他信息", additional_info)
        recalled_facts += "\n"

    state["recalled_facts_from_db"] = recalled_facts
    return {
        "recalled_facts_from_db": recalled_facts,
    }


# todo：接入火山Viking记忆库
async def nodeRecallFromViking(state: VirtualFigureGraphState) -> dict:
    logger.info("nodeRecallFromViking is called")

    state["recalled_facts_from_viking"] = []
    return {
        "recalled_facts_from_viking": state["recalled_facts_from_viking"],
    }


async def nodeBuildMessage(state: VirtualFigureGraphState) -> dict:
    logger.info("nodeBuildMessage is called")

    messages_received_json = state["request"]["messages_received"]
    messages_received_parsed = [msg["message"] for msg in messages_received_json]
    reply_prompt = "\n".join(messages_received_parsed)

    state["messages"].append(HumanMessage(content=reply_prompt or ""))
    return {
        "messages": state["messages"],
    }


async def nodeCallLLM(state: VirtualFigureGraphState) -> VirtualFigureGraphOutput:
    logger.info("nodeCallLLM is called")

    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    messages_to_send = [
        # 1. 系统提示词
        SystemMessage(
            content=(
                await getPrompt(
                    os.getenv("VIRTUAL_FIGURE_SYSTEM_PROMPT"),
                    {
                        "words_to_user": state["words_to_user"],
                        "current_timestamp": current_timestamp,
                    },
                )
            )
        ),
        # 2. 关系与画像上下文
        SystemMessage(content=f"关系与画像上下文：\n{state['context_block']}"),
        # 3. DB召回的长期记忆（真实）
        SystemMessage(
            content=f"可能参考的召回的长期记忆：\n{state['recalled_facts_from_db']}"
        ),
        # 4. Viking召回的长期记忆（不可信）
        SystemMessage(
            content=f"可能参考的召回的长期记忆：\n{json.dumps(state['recalled_facts_from_viking'], ensure_ascii=False)}"
        ),
    ] + state["messages"]

    # 使用 Ark SDK 替换 LangChain ainvoke 拿reasoning_content
    # llm: ChatOpenAI = prepareLLM(model="DOUBAO_2_0_LITE", options={
    #     "temperature": 0.3,
    #     "reasoning_effort": "low",
    # })
    # response = await llm.ainvoke(messages_to_send)
    # response_content = response.content if hasattr(response, "content") else response

    resp = await arkAinvoke(
        model="DOUBAO_2_0_LITE",
        messages=messages_to_send,
        model_options={
            "temperature": 0.3,
            "reasoning_effort": "low",
        },
    )
    output = resp["output"]
    reasoning_content = resp["reasoning_content"]
    ai_message = resp["ai_message"]

    try:
        parsed_output = json.loads(output)
    except json.JSONDecodeError:
        logger.warning(f"Error parsing LLM response: {output}")
        state["llm_output"]["messages_to_send"] = []
        return {
            "llm_output": state["llm_output"],
        }

    if not isinstance(parsed_output, dict):
        logger.warning(f"Error parsing LLM response: {output}")
        state["llm_output"]["messages_to_send"] = []
        return {
            "llm_output": state["llm_output"],
        }

    state["llm_output"]["messages_to_send"] = parsed_output.get("messages_to_send", [])
    state["llm_output"]["reasoning_content"] = reasoning_content or ""

    # parse成功写入short-term memory
    state["messages"].append(ai_message)

    # todo: 调试，线上删
    logger.info(f"\n当前state：\n{state}\n\n")

    return {
        "llm_output": state["llm_output"],
        "messages": state["messages"],
    }
