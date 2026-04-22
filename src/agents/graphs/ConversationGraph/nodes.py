import json
import logging
import os
from datetime import datetime
from typing import List
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, BaseMessage
from langgraph.graph.message import RemoveMessage

from src.agents.graphs.ConversationGraph.state import (
    ConversationGraphOutput,
    ConversationGraphState,
)
from src.agents.llm import arkAinvoke, prepareLLM
from src.agents.prompt import getPrompt
from src.database.enums import FineGrainedFeedDimension
from src.database.index import session
from src.services.fine_grained_feed import recallFineGrainedFeeds
from src.services.figure_and_relation import buildFigurePersonaMarkdown
from src.utils.index import checkFigureAndRelationOwnership, stringifyValue


logger = logging.getLogger(__name__)


def _getMessageCharCount(message: BaseMessage) -> int:
    """
    计算消息内容的字符数
    """
    return len(stringifyValue(getattr(message, "content", ""), strip=False))


def _stringifyMessagesForSummary(messages: List[BaseMessage]) -> str:
    """
    将消息列表文本化，用于注入模型进行摘要生成
    """
    lines: list[str] = []
    for message in messages:
        content = stringifyValue(getattr(message, "content", ""))
        if content == "":
            continue
        role = type(message).__name__
        lines.append(f"[{role}]\n{content}")
    return "\n\n".join(lines)


async def _summarizeTrimmedMessages(
    old_summary: str,
    messages_to_summarize: List[BaseMessage],
) -> str:
    """
    对消息进行滚动总结
    """
    if not messages_to_summarize:
        return old_summary.strip()

    summary_llm = prepareLLM(
        "DOUBAO_2_0_MINI",
        options={
            "temperature": 0,
            "reasoning_effort": "minimal",
        },
    )
    SUMMARY_MESSAGES_FOR_TRIM = await getPrompt(os.getenv("SUMMARY_MESSAGES_FOR_TRIM"))
    if not SUMMARY_MESSAGES_FOR_TRIM:
        raise ValueError("SUMMARY_MESSAGES_FOR_TRIM prompt not found")

    old_summary = old_summary.strip()
    messages_block = _stringifyMessagesForSummary(messages_to_summarize)
    user_prompt = (
        f"旧摘要：\n{old_summary or '无'}\n\n"
        f"需要新纳入摘要的更早消息：\n{messages_block or '无'}"
    )
    response = await summary_llm.ainvoke(
        [
            SystemMessage(content=SUMMARY_MESSAGES_FOR_TRIM),
            HumanMessage(content=user_prompt),
        ]
    )
    return stringifyValue(response.content, strip=False) or old_summary


async def _buildTrimmedShortTermMemory(
    messages: List[BaseMessage],  # 当前 session 中储存的全部消息
    old_summary: str,  # 旧的短期记忆摘要
) -> tuple[List[BaseMessage], str, List[RemoveMessage], dict[str, int]]:
    """
    修剪短期记忆

    当 messages 的总字符数或消息条数超过阈值时，从最早的消息开始裁剪，
    将被裁掉的历史消息与旧摘要一起交给 mini 模型滚动总结为新的 conversation_summary，
    同时生成对应的 RemoveMessage 列表，供 MessagesState 删除旧消息。
    无论是否触发裁剪，都会保留最新的一条消息，避免丢失当前轮输入。

    返回：
    - 修剪后的消息列表
    - 新的 conversation_summary
    - 删除旧消息的 RemoveMessage 列表
    - 修剪统计信息
    """
    total_chars_before_trim = sum(_getMessageCharCount(message) for message in messages)
    messages_count_before_trim = len(messages)
    if total_chars_before_trim <= int(
        os.getenv("SHORT_TERM_MEMORY_MAX_CHARS", "4000")
    ) and messages_count_before_trim <= int(
        os.getenv("SHORT_TERM_MEMORY_MAX_MESSAGES", "12")
    ):
        # 字符数和消息条数都在阈值内，无需裁剪
        return (
            messages,
            old_summary.strip(),
            [],
            {
                "messages_count_before_trim": messages_count_before_trim,
                "messages_count_after": messages_count_before_trim,
                "chars_before": total_chars_before_trim,
                "chars_after": total_chars_before_trim,
                "trimmed_count": 0,
            },
        )

    messages_after_trim = list(messages)  # 修剪后剩余的消息
    messages_to_summarize: List[BaseMessage] = []  # 待 summarize 的消息
    kept_chars = total_chars_before_trim  # 剩余的字符数

    while len(messages_after_trim) > 1 and (
        kept_chars > int(os.getenv("SHORT_TERM_MEMORY_TARGET_CHARS", "2800"))
        or len(messages_after_trim)
        > int(os.getenv("SHORT_TERM_MEMORY_MAX_MESSAGES", "12"))
    ):
        # 从最早的消息开始裁剪，直到剩余的字符数小于等于目标字符数或消息条数小于等于阈值
        removed_message = messages_after_trim.pop(0)
        messages_to_summarize.append(removed_message)
        kept_chars -= _getMessageCharCount(removed_message)

    new_summary = await _summarizeTrimmedMessages(old_summary, messages_to_summarize)
    remove_messages = [
        RemoveMessage(id=message.id)
        for message in messages_to_summarize
        if getattr(message, "id", None)
    ]
    return (
        messages_after_trim,
        new_summary,
        remove_messages,
        {
            "messages_count_before_trim": messages_count_before_trim,
            "messages_count_after": len(messages_after_trim),
            "chars_before": total_chars_before_trim,
            "chars_after": max(kept_chars, 0),
            "trimmed_count": len(messages_to_summarize),
        },
    )


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
        recalled_score = item.get("score")
        if isinstance(recalled_score, (int, float)):
            meta.append(f"综合分数（越高相关性和置信度越高）={recalled_score:.4f}")

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

        figure_persona = buildFigurePersonaMarkdown(
            fr=figure_and_relation,
            exclude_fields=[
                "words_figure2user",
                "words_user2figure",
                "core_procedural_info",
                "core_memory",
            ],  # 不包含在其他部分被注入的字段
        )
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
            "user_name": figure_and_relation.user.username,
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
        scope=[
            # 重大改动：完全不从 db 召回这两个低语境依赖的信息，避免和 persona 重复注入
            # {
            #     "scope": FineGrainedFeedDimension.PERSONALITY,
            #     "top_k": int(
            #         os.getenv("TOP_K_PERSONALITY_FEEDS_FOR_CONVERSATION", "3")
            #     ),
            # },
            # {
            #     "scope": FineGrainedFeedDimension.INTERACTION_STYLE,
            #     "top_k": int(
            #         os.getenv("TOP_K_INTERACTION_FEEDS_FOR_CONVERSATION", "3")
            #     ),
            # },
            {
                "scope": FineGrainedFeedDimension.PROCEDURAL_INFO,
                "top_k": int(
                    os.getenv("TOP_K_PROCEDURAL_FEEDS_FOR_CONVERSATION", "10")
                ),
            },
            {
                "scope": FineGrainedFeedDimension.MEMORY,
                "top_k": int(os.getenv("TOP_K_MEMORY_FEEDS_FOR_CONVERSATION", "10")),
            },
        ],
        query=query,
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
    # recalled_personalities_from_db = _recalledFeeds2Markdown(
    #     raw_items.get("personality", [])
    # )
    # recalled_interaction_styles_from_db = _recalledFeeds2Markdown(
    #     raw_items.get("interaction_style", [])
    # )
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
        # "recalled_personalities_from_db": recalled_personalities_from_db,
        # "recalled_interaction_styles_from_db": recalled_interaction_styles_from_db,
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


async def nodeBuildAndTrimMessage(state: ConversationGraphState) -> dict:
    """
    构建本轮消息并 trim messages
    """
    logger.info("nodeBuildAndTrimMessage is called")

    messages = state.get("messages") or []
    old_summary = state.get("conversation_summary") or ""
    logs = state.get("logs") or []
    messages_received = state["request"]["messages_received"]
    messages_received = "\n".join(messages_received)
    messages.append(HumanMessage(content=messages_received or ""))

    (
        trimmed_messages,
        conversation_summary,
        remove_messages,
        trim_stats,
    ) = await _buildTrimmedShortTermMemory(
        messages=messages,
        old_summary=old_summary,
    )

    logs += [
        {
            "step": "nodeBuildAndTrimMessage",
            "status": "ok",
            "detail": "Build current human message and trim short-term memory",
            "data": trim_stats,
        }
    ]
    logger.info(f"nodeBuildAndTrimMessage executed finished\n")
    return {
        "conversation_summary": conversation_summary,
        # `messages` 在 MessagesState 中是增量合并，不是整表覆盖。
        # 这里返回的是对已有 messages 的 patch：
        # 1. 用 RemoveMessage 删除被 trim 掉的旧消息；
        # 2. 只追加本轮新收到的 HumanMessage。
        # trimmed_messages 中其余未被删除的旧消息，本来就已经在 state 里，
        # 因此不需要重复返回。
        "messages": remove_messages + trimmed_messages[-1:],
        "logs": logs,
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
    conversation_summary = (state.get("conversation_summary") or "").strip()

    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    CONVERSATION_SYSTEM_PROMPT = await getPrompt(
        os.getenv("CONVERSATION_SYSTEM_PROMPT"),
        {
            "words_to_user": state["words_to_user"],
            "current_timestamp": current_timestamp,
            "user_name": state["user_name"],
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

    # 重大改动：完全不从 db 召回这两个低语境依赖的信息，避免和 persona 重复注入
    # low_context_depended_feeds = f"**注意**：以下信息作为关系与人物画像的补充。\n\n# 核心价值观与思维方式：\n{state['recalled_personalities_from_db']}\n\n# 沟通风格与反应模式：\n{state['recalled_interaction_styles_from_db']}"
    high_context_depended_feeds = f"**注意**：以下信息仅供参考，只有和当前语境相关时需要使用，否则请忽略。\n\n# 人生经历和重要故事：\n{state.get('recalled_memories_from_db', '')}\n\n# 核心程序性知识（ta怎么做事、工作方法）：\n{state.get('recalled_procedural_infos_from_db', '')}\n"

    messages_to_send = [
        # 1. 系统提示词
        SystemMessage(content=CONVERSATION_SYSTEM_PROMPT),
        # 2. 关系与画像上下文
        SystemMessage(content=f"关系与人物画像：\n{state['figure_persona']}"),
        # # 3. DB召回的长期记忆（真实）
        # SystemMessage(content=low_context_depended_feeds),
        SystemMessage(content=high_context_depended_feeds),
        # # 4. Viking召回的长期记忆（不可信）
        # SystemMessage(
        #     content=f"可能参考的召回的长期记忆：\n{json.dumps(state['recalled_facts_from_viking'], ensure_ascii=False)}"
        # ),
    ]
    # 5. 更早对话的滚动摘要
    if conversation_summary != "":
        messages_to_send.append(
            SystemMessage(content=f"以下是更早对话的摘要：\n{conversation_summary}")
        )
    # 6. 本轮消息 + 短期记忆
    messages_to_send += messages

    # 使用 Ark SDK 替换 LangChain ainvoke 拿reasoning_content
    # llm: ChatOpenAI = prepareLLM(model="DOUBAO_2_0_LITE", options={
    #     "temperature": 0.3,
    #     "reasoning_effort": "low",
    # })
    # response = await llm.ainvoke(messages_to_send)
    # response_content = response.content if hasattr(response, "content") else response

    logger.info(f"\nmessages_to_send:\n{messages_to_send}\n\n")

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

    raw_messages = parsed_output.get("messages_to_send", [])

    if raw_messages is None:
        figure_messages_this_round = []
    elif isinstance(raw_messages, str):
        figure_messages_this_round = [raw_messages]
    elif isinstance(raw_messages, list):
        figure_messages_this_round = [m for m in raw_messages if isinstance(m, str)]
    else:
        figure_messages_this_round = []

    llm_output["messages_to_send"] = figure_messages_this_round
    llm_output["reasoning_content"] = reasoning_content or ""

    # AI 回复写入 short-term memory
    next_messages = messages
    if figure_messages_this_round:
        next_messages = messages + [
            AIMessage(content="\n".join(figure_messages_this_round))
        ]
    logs += [
        {
            "step": "nodeCallLLM",
            "status": "ok",
            "detail": "LLM response generated",
            "data": {
                "messages_to_send_count": len(figure_messages_this_round),
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
