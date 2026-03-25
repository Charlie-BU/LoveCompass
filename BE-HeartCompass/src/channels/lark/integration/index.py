import asyncio
import logging
import os
import threading
import time
from typing import Any, List

from src.agent.graph.VirtualFigureGraph.graph import getVirtualFigureGraph
from src.agent.graph.VirtualFigureGraph.state import (
    VirtualFigureGraphOutput,
    initVirtualFigureGraphState,
)
from src.channels.lark.client import larkClient
from src.channels.lark.composite_api.im.send_text import SendTextRequest, sendText
from src.channels.lark.integration.menu import handleMenuCommand
from src.database.database import session
from src.database.models import RelationChain, User

logger = logging.getLogger(__name__)
_lark_client = larkClient()

# 每个用户当前激活的关系链
_active_relation_chain_by_open_id: dict[str, int] = {}
# 每个用户待处理的消息队列
_pending_messages_by_open_id: dict[str, list[dict[str, Any]]] = {}
# 每个用户的计时器
_flush_timer_by_open_id: dict[str, threading.Timer] = {}
# 全局状态锁
_state_lock = threading.Lock()

# 为了防止飞书 SDK 问题导致重复接受消息，暂存已接收的消息和接收时间戳
_temp_received_messages_by_open_id: dict[str, list[tuple[str, int]]] = {}


def getUserIdByOpenId(open_id: str) -> int | None:
    with session() as db:
        user = db.query(User).filter(User.lark_open_id == open_id).first()
        if user is None:
            logger.warning(f"open_id：{open_id} 未授权")
            return None
        return user.id


def relationChainBelongsToUser(user_id: int, relation_chain_id: int) -> bool:
    with session() as db:
        relation_chain = db.get(RelationChain, relation_chain_id)
        if relation_chain is None:
            return False
        return relation_chain.user_id == user_id


def sendText2OpenId(open_id: str, text: str) -> None:
    response = sendText(
        _lark_client,
        SendTextRequest(
            text=text,
            receive_id_type="open_id",
            receive_id=open_id,
        ),
    )
    if getattr(response, "code", None) != 0:
        logger.error(
            f"发送飞书消息失败，open_id：{open_id}，code：{response.code}，msg：{response.msg}"
        )


def getWaitingSeconds() -> int:
    waiting_seconds = int(os.getenv("WAITING_SECONDS_FOR_VIRTUAL_FIGURE") or "15")
    return max(waiting_seconds, 1)


def normalizeReply(item: Any) -> str | None:
    if isinstance(item, str):
        stripped = item.strip()
        return stripped if stripped else None
    if isinstance(item, dict):
        message = item.get("message")
        if isinstance(message, str):
            stripped = message.strip()
            return stripped if stripped else None
    return None


async def processMessages(
    user_id: int, relation_chain_id: int, messages: list[dict[str, Any]]
) -> tuple[List[str], str]:
    session_start = time.perf_counter()
    logger.info(f"开始处理本批次消息：{messages}")
    graph = getVirtualFigureGraph()
    short_term_memory_config = {"configurable": {"thread_id": str(relation_chain_id)}}
    state = initVirtualFigureGraphState(
        {
            "user_id": user_id,
            "relation_chain_id": relation_chain_id,
            "messages_received": messages,
        }
    )
    response: VirtualFigureGraphOutput = await graph.ainvoke(
        state, config=short_term_memory_config
    )
    logger.info(f"处理完成，耗时：{time.perf_counter() - session_start}s")
    return (
        response["llm_output"].get("messages_to_send", []),
        response["llm_output"].get("reasoning_content", ""),
    )


# 取消并删除open_id对应的计时器
def _cancelFlushTimerLocked(open_id: str) -> None:
    timer = _flush_timer_by_open_id.get(open_id)
    if timer and timer.is_alive():
        timer.cancel()
    _flush_timer_by_open_id.pop(open_id, None)


def _sendBatchMessages(open_id: str) -> None:
    with _state_lock:
        messages_to_process = _pending_messages_by_open_id.pop(open_id, [])
        _flush_timer_by_open_id.pop(open_id, None)  # 删除open_id对应的计时器

    if not messages_to_process:
        return

    user_id = getUserIdByOpenId(open_id)
    if user_id is None:
        sendText2OpenId(open_id, "【System】当前账号未授权，请先绑定账号")
        return

    with _state_lock:
        relation_chain_id = _active_relation_chain_by_open_id.get(open_id)
    if relation_chain_id is None:
        sendText2OpenId(
            open_id, "【System】请先通过 /<crush_id> 切换当前对话对象，例如 /1"
        )
        return

    if not relationChainBelongsToUser(user_id, relation_chain_id):
        with _state_lock:
            _active_relation_chain_by_open_id.pop(open_id, None)
        sendText2OpenId(
            open_id, "【System】当前对话对象不可用，请重新发送 /<crush_id> 切换"
        )
        return

    try:
        messages_to_send, reasoning_content = asyncio.run(
            processMessages(
                user_id=user_id,
                relation_chain_id=relation_chain_id,
                messages=messages_to_process,
            )
        )
    except Exception as e:
        logger.error(f"批量处理消息失败，open_id：{open_id}，err：{e}", exc_info=True)
        sendText2OpenId(open_id, "【System】消息处理失败，请稍后重试")
        return

    for item in messages_to_send:
        text = normalizeReply(item)
        if text is not None:
            sendText2OpenId(open_id, text)


def _scheduleFlush(open_id: str) -> None:
    waiting_seconds = getWaitingSeconds()
    with _state_lock:
        # 删除open_id对应的计时器，重新创建一个新的
        _cancelFlushTimerLocked(open_id)
        flush_timer = threading.Timer(
            waiting_seconds, _sendBatchMessages, args=(open_id,)
        )
        flush_timer.daemon = True  # 设为守护线程，主线程退出时自动结束
        _flush_timer_by_open_id[open_id] = flush_timer
        flush_timer.start()


# 过滤重复消息
def filterDuplicatedMessage(message: str, open_id: str) -> bool:
    current_time = int(time.time())
    second_threshold = (
        10 if message.startswith("/") else 30
    )  # 30秒内完全相同消息视为重复，菜单命令10秒内视为重复
    is_duplicate = False

    with _state_lock:
        received_messages = _temp_received_messages_by_open_id.get(open_id, [])
        updated_received_messages = []
        # 虽然时间复杂度高，但能保证超出30s的消息可以及时被清理
        for msg, ts in received_messages:
            if current_time - ts < second_threshold:
                if msg == message:
                    # 30s内有相同消息，判定重复，不继续处理
                    logger.info(f"重复消息：{message}，已过滤")
                    is_duplicate = True
                # received_messages 中保留发送到现在30秒内的消息
                updated_received_messages.append((msg, ts))
            # received_messages 中超过30秒的消息，丢弃

        # 将当前这条新消息加入去重缓存
        if not is_duplicate:
            updated_received_messages.append((message, current_time))
        _temp_received_messages_by_open_id[open_id] = updated_received_messages

    return is_duplicate


def messageHandler(message: str, open_id: str) -> None:
    # 过滤重复消息
    if filterDuplicatedMessage(message, open_id):
        return

    logger.info(f"收到：{message}")

    if handleMenuCommand(message, open_id):
        return

    user_id = getUserIdByOpenId(open_id)
    if user_id is None:
        sendText2OpenId(open_id, "【System】当前账号未授权，请先绑定账号")
        return

    relation_chain_id = _active_relation_chain_by_open_id.get(open_id)
    if relation_chain_id is None:
        sendText2OpenId(
            open_id, "【System】请先通过 /<crush_id> 切换当前对话对象，例如 /1"
        )
        return

    if not relationChainBelongsToUser(user_id, relation_chain_id):
        with _state_lock:
            _active_relation_chain_by_open_id.pop(open_id, None)
        sendText2OpenId(
            open_id, "【System】当前对话对象不可用，请重新发送 /<crush_id> 切换"
        )
        return

    # 只入队不立即处理：最后一条消息后等待 WAITING_SECONDS_FOR_VIRTUAL_FIGURE 秒再批量处理
    with _state_lock:
        buffered_messages = _pending_messages_by_open_id.setdefault(open_id, [])
        buffered_messages.append(
            {
                "relation_chain_id": relation_chain_id,
                "message": message,
            }
        )
    _scheduleFlush(open_id)
