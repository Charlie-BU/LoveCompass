from langchain_core.messages import SystemMessage, HumanMessage
import json
import logging
import os
from datetime import datetime

from src.agents.graphs.ConversationGraph.state import (
    ConversationGraphOutput,
    ConversationGraphState,
)
from src.agents.llm import arkAinvoke
from src.agents.prompt import getPrompt
from src.database.enums import FineGrainedFeedDimension
from src.database.index import session
from src.services.fine_grained_feed import recallFineGrainedFeeds
from src.services.figure_and_relation import buildFigurePersonaMarkdown
from src.utils.index import checkFigureAndRelationOwnership


logger = logging.getLogger(__name__)


def _recalledFeeds2Markdown(items: list[dict]) -> str:
    """
    格式化召回结果为 Markdown
    """
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        feed = item.get("fine_grained_feed") or {}
        content = (feed.get("content") or "").strip()
        if content == "":
            continue
        sub_dimension = feed.get("sub_dimension") or ""

        meta: list[str] = []
        confidence = feed.get("confidence") or ""
        recalled_score = item.get("score")
        if confidence:
            meta.append(f"confidence={confidence}")
        if isinstance(recalled_score, (int, float)):
            meta.append(f"recalled_score={recalled_score:.4f}")

        suffix = f" ({', '.join(meta)})" if meta else ""
        lines.append(f"{index}. {sub_dimension}\n{content}\n{suffix}")
    return "\n\n".join(lines)


def nodeLoadFRAndPersona(state: ConversationGraphState) -> dict:
    """
    加载当前 figure_and_relation 及其人物画像
    """
    logger.info("nodeLoadFRAndPersona is called")
    request = state["request"]

    with session() as db:
        figure_and_relation = checkFigureAndRelationOwnership(
            db=db, user_id=request["user_id"], fr_id=request["fr_id"]
        )
        if figure_and_relation is None:
            logger.error("Figure and relation not found")
            raise ValueError("Figure and relation not found")

        figure_persona = buildFigurePersonaMarkdown(figure_and_relation)
        words_to_user = figure_and_relation.words_figure2user
        # 追加节点执行日志，保留上游日志链路
        logs = state.get("logs") or []
        logs += [
            {
                "step": "nodeLoadFRAndPersona",
                "status": "ok",
                "detail": "FigureAndRelation loaded",
                "data": {
                    "fr_id": request["fr_id"],
                    "figure_role": figure_and_relation.figure_role,
                },
            }
        ]
        logger.info("nodeLoadFRAndPersona executed finished\n")
        return {
            "figure_and_relation": figure_and_relation.toJson(),
            "figure_persona": figure_persona,
            "words_to_user": ", ".join(words_to_user),
            "logs": logs,
        }


async def nodeRecallFeedsFromDB(state: ConversationGraphState) -> dict:
    """
    从数据库分组召回 personality, interaction style, procedural info, memory feeds
    """
    logger.info("nodeRecallFeedsFromDB is called")
    warnings = state.get("warnings") or []
    errors = state.get("errors") or []
    logs = state.get("logs") or []

    request = state["request"]
    user_id = request["user_id"]
    fr_id = request["fr_id"]
    messages_received = request["messages_received"]
    if not isinstance(messages_received, list):
        messages_received = []
    query = ". ".join([item for item in messages_received if isinstance(item, str)])

    if not isinstance(query, str) or query.strip() == "":
        warning_message = f"Messages_received is empty"
        logger.warning(warning_message)
        warnings += [warning_message]
        logs += [
            {
                "step": "nodeRecallFeedsFromDB",
                "status": "skip",
                "detail": "Skip recall because messages_received is empty",
                "data": {
                    "fr_id": fr_id,
                },
            }
        ]
        logger.info("nodeRecallFeedsFromDB executed finished\n")
        return {
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    recalled = await recallFineGrainedFeeds(
        user_id=user_id,
        fr_id=fr_id,
        query=query,
        scope=[
            {
                "scope": FineGrainedFeedDimension.PERSONALITY,
                "top_k": int(os.getenv("TOP_K_FEEDS_FOR_PERSONALITY_RECALL", "20")),
            },
            {
                "scope": FineGrainedFeedDimension.INTERACTION_STYLE,
                "top_k": int(
                    os.getenv("TOP_K_FEEDS_FOR_INTERACTION_STYLE_RECALL", "20")
                ),
            },
            {
                "scope": FineGrainedFeedDimension.PROCEDURAL_INFO,
                "top_k": int(os.getenv("TOP_K_FEEDS_FOR_PROCEDURAL_INFO_RECALL", "20")),
            },
            {
                "scope": FineGrainedFeedDimension.MEMORY,
                "top_k": int(os.getenv("TOP_K_FEEDS_FOR_MEMORY_RECALL", "20")),
            },
        ],
    )
    if recalled.get("status") != 200:
        error_message = f"Recall failed: {recalled.get('message', 'Unknown error')}"
        logger.warning(f"Recall failed: {recalled}")
        errors += [error_message]
        logs += [
            {
                "step": "nodeRecallFeedsFromDB",
                "status": "error",
                "detail": "Recall fine-grained feeds failed",
                "data": {
                    "fr_id": fr_id,
                    "status": recalled.get("status"),
                    "message": recalled.get("message"),
                },
            }
        ]
        logger.info("nodeRecallFeedsFromDB executed finished\n")
        return {
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    raw_items = recalled.get("items") or {}
    if not isinstance(raw_items, dict):
        raw_items = {}
    recalled_personalities_from_db = _recalledFeeds2Markdown(
        raw_items.get("personality", [])
    )
    recalled_interaction_styles_from_db = _recalledFeeds2Markdown(
        raw_items.get("interaction_style", [])
    )
    recalled_procedural_infos_from_db = _recalledFeeds2Markdown(
        raw_items.get("procedural_info", [])
    )
    recalled_memories_from_db = _recalledFeeds2Markdown(raw_items.get("memory", []))

    recalled_count = (
        len(raw_items.get("personality", []))
        + len(raw_items.get("interaction_style", []))
        + len(raw_items.get("procedural_info", []))
        + len(raw_items.get("memory", []))
    )

    logs += [
        {
            "step": "nodeRecallFeedsFromDB",
            "status": "ok",
            "detail": "Recall fine-grained feeds success",
            "data": {
                "fr_id": fr_id,
                "recalled_count": recalled_count,
            },
        }
    ]
    logger.info("nodeRecallFeedsFromDB executed finished\n")
    return {
        "recalled_personalities_from_db": recalled_personalities_from_db,
        "recalled_interaction_styles_from_db": recalled_interaction_styles_from_db,
        "recalled_procedural_infos_from_db": recalled_procedural_infos_from_db,
        "recalled_memories_from_db": recalled_memories_from_db,
        "warnings": warnings,
        "errors": errors,
        "logs": logs,
    }


# todo：接入火山 Viking 记忆库
# async def nodeRecallFactsFromViking(state: ConversationGraphState) -> dict:
#     """
#     从 Viking 记忆库中召回记忆
#     """


async def nodeBuildMessage(state: ConversationGraphState) -> dict:
    logger.info("nodeBuildMessage is called")

    messages = state.get("messages") or []
    messages_received = state["request"]["messages_received"]
    messages_received = "\n".join(messages_received)

    messages.append(HumanMessage(content=messages_received or ""))
    logger.info(f"nodeBuildMessage executed finished\n")
    return {
        "messages": messages,
    }


async def nodeCallLLM(state: ConversationGraphState) -> ConversationGraphOutput:
    """
    调用 LLM 生成回复
    """
    logger.info("nodeCallLLM is called")
    warnings = state.get("warnings") or []
    errors = state.get("errors") or []
    logs = state.get("logs") or []
    llm_output = state.get("llm_output") or {
        "messages_to_send": [],
        "reasoning_content": "",
    }
    messages = state.get("messages") or []

    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    CONVERSATION_SYSTEM_PROMPT = await getPrompt(
        os.getenv("CONVERSATION_SYSTEM_PROMPT"),
        {
            "words_to_user": state["words_to_user"],
            "current_timestamp": current_timestamp,
        },
    )
    if not CONVERSATION_SYSTEM_PROMPT:
        error_message = "nodeCallLLM failed: CONVERSATION_SYSTEM_PROMPT is empty"
        logger.error(error_message)
        errors += [error_message]
        logs += [
            {
                "step": "nodeCallLLM",
                "status": "error",
                "detail": "System prompt is empty",
                "data": {},
            }
        ]
        logger.info("nodeCallLLM executed finished\n")
        llm_output["messages_to_send"] = []
        llm_output["reasoning_content"] = ""
        return {
            "llm_output": llm_output,
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    low_context_depended_feeds = f"**注意**：以下信息作为关系与人物画像的补充。\n\n# 核心价值观与思维方式：\n{state['recalled_personalities_from_db']}\n\n# 沟通风格与反应模式：\n{state['recalled_interaction_styles_from_db']}"
    high_context_depended_feeds = f"**注意**：以下信息仅供参考，只有和当前语境相关时需要使用，否则请忽略。\n\n# 核心程序性知识（ta怎么做事、工作方法）：\n{state['recalled_procedural_infos_from_db']}\n\n# 人生经历和重要故事：\n{state['recalled_memories_from_db']}\n"

    messages_to_send = [
        # 1. 系统提示词
        SystemMessage(content=CONVERSATION_SYSTEM_PROMPT),
        # 2. 关系与画像上下文
        SystemMessage(content=f"关系与人物画像：\n{state['figure_persona']}"),
        # # 3. DB召回的长期记忆（真实）
        SystemMessage(content=low_context_depended_feeds),
        SystemMessage(content=high_context_depended_feeds),
        # # 4. Viking召回的长期记忆（不可信）
        # SystemMessage(
        #     content=f"可能参考的召回的长期记忆：\n{json.dumps(state['recalled_facts_from_viking'], ensure_ascii=False)}"
        # ),
    ] + messages

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
        reasoning_content_in_ai_message=False,  # 不把 reasoning_content 放到 AIMessage 中，压缩 AIMessage 体积
    )
    output = resp["output"]
    reasoning_content = resp["reasoning_content"]
    ai_message = resp["ai_message"]

    try:
        parsed_output = json.loads(output)
    except json.JSONDecodeError:
        warning_message = "nodeCallLLM: failed to parse JSON output from LLM"
        logger.warning(f"{warning_message}: {output}")
        warnings += [warning_message]
        logs += [
            {
                "step": "nodeCallLLM",
                "status": "error",
                "detail": "LLM output is not valid JSON",
                "data": {"raw_output": output},
            }
        ]
        llm_output["messages_to_send"] = []
        llm_output["reasoning_content"] = reasoning_content or ""
        logger.info("nodeCallLLM executed finished\n")
        return {
            "llm_output": llm_output,
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    if not isinstance(parsed_output, dict):
        warning_message = "nodeCallLLM: parsed output is not a dict"
        logger.warning(f"{warning_message}: {output}")
        warnings += [warning_message]
        logs += [
            {
                "step": "nodeCallLLM",
                "status": "error",
                "detail": "LLM output JSON is not an object",
                "data": {"parsed_output_type": str(type(parsed_output))},
            }
        ]
        llm_output["messages_to_send"] = []
        llm_output["reasoning_content"] = reasoning_content or ""
        logger.info("nodeCallLLM executed finished\n")
        return {
            "llm_output": llm_output,
            "warnings": warnings,
            "errors": errors,
            "logs": logs,
        }

    llm_output["messages_to_send"] = parsed_output.get("messages_to_send", [])
    llm_output["reasoning_content"] = reasoning_content or ""

    # parse成功写入short-term memory
    next_messages = messages + [ai_message]
    logs += [
        {
            "step": "nodeCallLLM",
            "status": "ok",
            "detail": "LLM response generated",
            "data": {
                "messages_to_send_count": len(llm_output["messages_to_send"]),
            },
        }
    ]

    logger.info("nodeCallLLM executed finished\n")

    # todo: 测试，上线删
    print("\n")
    # pprint.pprint(state, indent=2)
    logger.info(f"\nllm_output: {llm_output}\n")
    logger.info(f"next_messages: {next_messages}\n")

    return {
        "llm_output": llm_output,
        "messages": next_messages,
        "warnings": warnings,
        "errors": errors,
        "logs": logs,
    }
