import asyncio
import logging
import os
import threading
import time
from typing import Any, List

from src.agents.graphs.ConversationGraph.graph import getConversationGraph
from src.agents.graphs.ConversationGraph.state import ConversationGraphOutput
from src.channels.lark.integration.utils import (
    frBelongsToUser,
    sendCard2OpenId,
    sendText2OpenId,
)
from src.channels.lark.integration.menu import handleMenuCommand
from src.cli.session import saveLocalSession
from src.cli.utils import getCurrentUserFromLocalSession
from src.service_dispatcher import dispatchServiceCall
from src.services.user import (
    getUserIdByAccessToken,
    getUserIdByOpenId,
    userLogin,
    userLoginByOpenId,
)


logger = logging.getLogger(__name__)

# 以下 by_open_id 的原因是系统里可能有多个用户并发，每个用户各自一个激活 FR（暂未实现，留扩展性）
# 每个用户当前激活的 openid-fr_id 映射
_active_fr_by_open_id: dict[str, int] = {}
# 每个用户待处理的消息队列
_pending_messages_by_open_id: dict[str, list[str]] = {}
# 每个用户的计时器
_flush_timer_by_open_id: dict[str, threading.Timer] = {}
# 全局状态锁
_state_lock = threading.Lock()
# 为了防止飞书 SDK 问题导致重复接收消息，暂存已接收的消息和接收时间戳
_temp_received_messages_by_open_id: dict[str, list[tuple[str, int]]] = {}

# 说明：
# - ConversationGraph 使用了异步 checkpointer，连接生命周期依赖事件循环
# - 若每次批处理都用 asyncio.run(...)，会反复创建并关闭 loop，导致第二次调用可能出现 "the connection is closed"（复用到已失效连接）
# - 这里改为进程级单一后台 loop，配合 run_coroutine_threadsafe 执行异步任务，确保连接稳定复用

# 异步事件循环
_async_loop: asyncio.AbstractEventLoop | None = None
# 异步事件循环线程
_async_loop_thread: threading.Thread | None = None
# 异步事件循环锁
_async_loop_lock = threading.Lock()


def _runLoop(loop: asyncio.AbstractEventLoop) -> None:
    """
    异步事件循环线程函数
    """
    asyncio.set_event_loop(loop)
    loop.run_forever()


def _getOrCreateAsyncLoop() -> asyncio.AbstractEventLoop:
    """
    获取或创建异步事件循环
    """
    global _async_loop, _async_loop_thread
    with _async_loop_lock:
        if _async_loop is not None and _async_loop.is_running():
            return _async_loop

        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(
            target=_runLoop,
            args=(loop,),
            name="lark-integration-async-loop",
            daemon=True,
        )
        loop_thread.start()

        _async_loop = loop
        _async_loop_thread = loop_thread
        return _async_loop


def _runAsync(coro: Any, timeout_seconds: int = 120) -> Any:
    """
    在单一异步事件循环中运行异步任务
    """
    loop = _getOrCreateAsyncLoop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout_seconds)


async def processMessages(
    user_id: int, fr_id: int, messages: list[str]
) -> tuple[List[str], str]:
    """
    调用 ConversationGraph，批量处理本批次消息
    """
    session_start = time.perf_counter()
    logger.info(f"开始处理本批次消息：{messages}")

    graph = await getConversationGraph()
    short_term_memory_config = {"configurable": {"thread_id": str(fr_id)}}
    state = {
        "request": {
            "user_id": user_id,
            "fr_id": fr_id,
            "messages_received": messages,
        },
    }
    response: ConversationGraphOutput = await graph.ainvoke(
        state, config=short_term_memory_config
    )

    logger.info(f"处理完成，耗时：{time.perf_counter() - session_start}s")
    llm_output = response.get("llm_output", {})
    messages_to_send = llm_output.get("messages_to_send", []) if llm_output else []
    reasoning_content = llm_output.get("reasoning_content", "") if llm_output else ""
    return (messages_to_send, reasoning_content)


def _cancelFlushTimerLocked(open_id: str) -> None:
    """
    取消当前计时并删除 open_id 对应的计时器
    """
    timer = _flush_timer_by_open_id.get(open_id)
    if timer and timer.is_alive():
        timer.cancel()
    _flush_timer_by_open_id.pop(open_id, None)


def _sendBatchMessages(open_id: str) -> None:
    """
    异步调用 processMessages 处理本批次消息
    """
    with _state_lock:
        messages_to_process = _pending_messages_by_open_id.pop(open_id, [])
        # 删除当前计时器
        _flush_timer_by_open_id.pop(open_id, None)

    if not messages_to_process:
        return

    user_id = dispatchServiceCall(
        getUserIdByOpenId,
        {"open_id": open_id},
    ).get("user_id")

    if user_id is None:
        sendCard2OpenId(
            open_id=open_id,
            title="出错啦",
            content="当前飞书账号未授权，请先绑定账号",
            theme="red",
        )
        return

    with _state_lock:
        fr_id = _active_fr_by_open_id.get(open_id)
    if fr_id is None:
        sendCard2OpenId(
            open_id=open_id,
            title="Immortality 提示",
            content="请先发送 `/<fr_id>` 切换当前对话对象，例如 `/1`",
            theme="yellow",
        )
        return

    if not frBelongsToUser(user_id, fr_id):
        with _state_lock:
            _active_fr_by_open_id.pop(open_id, None)
        sendCard2OpenId(
            open_id=open_id,
            title="出错啦",
            content="当前对话对象不可用，请重新发送 `/<fr_id>` 切换",
            theme="red",
        )
        return

    try:
        messages_to_send, _ = _runAsync(
            processMessages(
                user_id=user_id,
                fr_id=fr_id,
                messages=messages_to_process,
            )
        )
    except Exception as e:
        logger.warning(f"Fail to process messages in batch: {e}", exc_info=True)
        sendCard2OpenId(
            open_id=open_id,
            title="出错啦",
            content="消息处理失败，请稍后重试",
            theme="red",
        )
        return

    for msg in messages_to_send:
        msg = msg.strip()
        if msg is not None and msg != "":
            sendText2OpenId(open_id, msg)


def _scheduleFlush(open_id: str) -> None:
    """
    重置计时器
    """
    waiting_seconds = int(os.getenv("WAITING_SECONDS_FOR_CONVERSATION") or "15")
    with _state_lock:
        # 删除 open_id 对应的计时器，重新创建一个新的
        _cancelFlushTimerLocked(open_id)
        flush_timer = threading.Timer(
            waiting_seconds,
            _sendBatchMessages,
            args=(open_id,),
        )
        flush_timer.daemon = True  # 设为守护线程，主线程退出时自动结束
        _flush_timer_by_open_id[open_id] = flush_timer
        flush_timer.start()


def filterDuplicatedMessage(message: str, open_id: str) -> bool:
    """
    过滤短时间内的完全重复消息
    """
    current_time = int(time.time())
    second_threshold = (
        10 if message.startswith("/") else 30
    )  # 30 秒内完全相同消息视为重复，菜单命令 10 秒内视为重复
    is_duplicate = False

    with _state_lock:
        received_messages = _temp_received_messages_by_open_id.get(open_id, [])
        updated_received_messages = []
        # 虽然时间复杂度高，但能保证超出阈值的消息可以及时被清理
        for msg, ts in received_messages:
            if current_time - ts < second_threshold:
                if msg == message:
                    logger.info(f"重复消息：{message}，已过滤")
                    is_duplicate = True
                updated_received_messages.append((msg, ts))

        if not is_duplicate:
            updated_received_messages.append((message, current_time))
        _temp_received_messages_by_open_id[open_id] = updated_received_messages

    return is_duplicate


def loginIfNeeded(open_id: str) -> bool:
    """
    token 过期时触发登录，保证本地 token 有效
    """
    try:
        # 从本地 session 中校验登录态并获取当前用户信息
        getCurrentUserFromLocalSession()
        return True
    except Exception:
        login_res = userLoginByOpenId(open_id)
        if login_res.get("status") != 200:
            sendCard2OpenId(
                open_id=open_id,
                title="出错啦",
                content="请稍后重试",
                theme="red",
            )
            return False
        saveLocalSession(
            {
                "access_token": login_res["access_token"],
                "user_id": login_res["user_id"],
            }
        )
        return True


def messageHandler(message: str, open_id: str) -> None:
    """
    消息处理入口
    """
    if filterDuplicatedMessage(message, open_id):
        return

    logger.info(f"Received: {message}")

    # token 过期时触发登录，保证本地 token 有效
    if not loginIfNeeded(open_id):
        return

    try:
        if handleMenuCommand(message, open_id):
            return
    except Exception as e:
        logger.warning(f"Fail to handle menu command: {e}")
        sendCard2OpenId(
            open_id=open_id,
            title="出错啦",
            content="菜单命令处理失败，请稍后重试",
            theme="red",
        )
        return

    user_id = dispatchServiceCall(
        getUserIdByOpenId,
        {"open_id": open_id},
    ).get("user_id")

    if user_id is None:
        sendCard2OpenId(
            open_id=open_id,
            title="出错啦",
            content="当前飞书账号未授权，请先绑定账号",
            theme="red",
        )
        return

    with _state_lock:
        fr_id = _active_fr_by_open_id.get(open_id)
    if fr_id is None:
        sendCard2OpenId(
            open_id=open_id,
            title="Immortality 提示",
            content="请先发送 `/<fr_id>` 切换当前对话对象，例如 `/1`",
            theme="yellow",
        )
        return

    if not frBelongsToUser(user_id, fr_id):
        with _state_lock:
            _active_fr_by_open_id.pop(open_id, None)
        sendCard2OpenId(
            open_id=open_id,
            title="出错啦",
            content="当前对话对象不可用，请重新发送 `/<fr_id>` 切换",
            theme="red",
        )
        return

    # 只入队不立即处理：最后一条消息后等待 WAITING_SECONDS 秒再批量处理
    with _state_lock:
        buffered_messages = _pending_messages_by_open_id.setdefault(open_id, [])
        buffered_messages.append(message)
    _scheduleFlush(open_id)
