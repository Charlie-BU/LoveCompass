from robyn import SubRouter, WebSocket, WebSocketDisconnect
import asyncio
import os

from ..services.user import userGetUserIdByAccessToken
from database.database import session
from database.models import RelationChain


virtual_figure_router = SubRouter(__file__, prefix="/virtual_figure")
# 全局单连接状态
_active_connection = {"websocket": None, "user_id": None, "relation_chain_id": None}
_active_lock = asyncio.Lock()


# 发送统一结构的错误消息
async def _sendError(
    websocket: WebSocket, relation_chain_id: int, message: str
) -> None:
    await websocket.send_json(
        {"relation_chain_id": relation_chain_id, "message": message}
    )


# 校验连接参数
async def _validateConnection(websocket: WebSocket) -> tuple[int, int] | None:
    relation_chain_id = websocket.query_params.get("relation_chain_id", None)
    if not relation_chain_id:
        await _sendError(websocket, -1, "relation_chain_id is required")
        await websocket.close()
        return None
    try:
        relation_chain_id = int(relation_chain_id)
    except Exception:
        await _sendError(websocket, -1, "relation_chain_id is invalid")
        await websocket.close()
        return None

    if os.getenv("CURRENT_ENV") != "dev":
        token = websocket.query_params.get("token")
        try:
            user_id = userGetUserIdByAccessToken(token=token)
        except Exception:
            await _sendError(websocket, relation_chain_id, "Invalid token")
            await websocket.close()
            return None
    else:
        user_id = 1

    with session() as db:
        relation_chain = db.get(RelationChain, relation_chain_id)
        if not relation_chain:
            await _sendError(websocket, relation_chain_id, "Relation chain not found")
            await websocket.close()
            return None
        if relation_chain.user_id != user_id:
            await _sendError(
                websocket, relation_chain_id, "You are not in this relation chain"
            )
            await websocket.close()
            return None

    return relation_chain_id, user_id


# mock 处理：将暂存消息映射为待发送结果
def _mockProcessMessages(relation_chain_id: int, temp_messages: list) -> list:
    messages_to_send = []
    for item in temp_messages:
        message = ""
        if isinstance(item, dict):
            message = item.get("message") or ""
        messages_to_send.append(
            {
                "relation_chain_id": relation_chain_id,
                "message": f"mock:{message}",
            }
        )
    return messages_to_send


# 发送暂存消息的处理结果并清空队列
async def _flushMessages(
    websocket: WebSocket, relation_chain_id: int, temp_messages: list
) -> None:
    if not temp_messages:
        return
    messages_to_send = _mockProcessMessages(relation_chain_id, temp_messages)
    for item in messages_to_send:
        await websocket.send_json(item)
    temp_messages.clear()


async def _handle(websocket: WebSocket) -> None:
    # 校验连接参数
    validated = await _validateConnection(websocket)
    if not validated:
        return
    relation_chain_id, user_id = validated

    # 确保只有一个连接 active
    async with _active_lock:
        if _active_connection["websocket"] is not None:
            await _sendError(
                websocket, relation_chain_id, "Only one websocket connection allowed"
            )
            await websocket.close()
            return
        _active_connection["websocket"] = websocket
        _active_connection["user_id"] = user_id
        _active_connection["relation_chain_id"] = relation_chain_id

    await websocket.send_json(
        {"relation_chain_id": relation_chain_id, "message": "connected"}
    )

    temp_messages = []
    inactivity_task = None  # 当前正在执行的scheduleFlush任务

    # 15 秒无新消息触发处理
    async def scheduleFlush():
        try:
            await asyncio.sleep(15)
            await _flushMessages(websocket, relation_chain_id, temp_messages)
        except asyncio.CancelledError:
            return

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except Exception:
                await _sendError(websocket, relation_chain_id, "receive error")
                continue
            if not isinstance(data, dict):
                await _sendError(websocket, relation_chain_id, "invalid message format")
                continue

            data_relation_chain_id = data.get("relation_chain_id", relation_chain_id)
            if data_relation_chain_id != relation_chain_id:
                await _sendError(
                    websocket, relation_chain_id, "Please finish current session first"
                )
                continue

            temp_messages.append(
                {
                    "relation_chain_id": data_relation_chain_id,
                    "message": data.get("message"),
                }
            )
            print("temp_messages:", temp_messages)

            # 取消当前定时任务，重新开始倒计时
            if inactivity_task:
                inactivity_task.cancel()
                try:
                    await inactivity_task
                except asyncio.CancelledError:
                    pass
            inactivity_task = asyncio.create_task(scheduleFlush())
    finally:
        # 关闭连接时清理定时任务与全局连接状态
        if inactivity_task:
            inactivity_task.cancel()
            try:
                await inactivity_task
            except asyncio.CancelledError:
                pass
        async with _active_lock:
            if _active_connection["websocket"] is websocket:
                _active_connection["websocket"] = None
                _active_connection["user_id"] = None
                _active_connection["relation_chain_id"] = None


@virtual_figure_router.websocket("/send")
async def send(websocket: WebSocket) -> None:
    await _handle(websocket)
