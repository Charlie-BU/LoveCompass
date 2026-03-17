import random
from robyn import Request, Response, SubRouter, WebSocket, WebSocketDisconnect
from robyn.authentication import BearerGetter
import asyncio
import os
import time
import logging

from ..authentication import AuthHandler
from ..services.user import userGetUserIdByAccessToken
from ..services.virtual_figure import vfRecalculateContextBlock
from src.database.database import session
from src.database.models import RelationChain
from src.agent.graph.VirtualFigureGraph.graph import getVirtualFigureGraph
from src.agent.graph.VirtualFigureGraph.state import (
    VirtualFigureGraphOutput,
    initVirtualFigureGraphState,
)


logger = logging.getLogger(__name__)
virtual_figure_router = SubRouter(__file__, prefix="/virtual_figure")


# 全局单连接状态
_active_connection = {"websocket": None, "user_id": None, "relation_chain_id": None}
_active_lock = asyncio.Lock()

# todo：心跳机制和断开重连


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


# 将消息递交agent，返回对方回复
# 注意：耗时操作
async def _processMessages(user_id: int, relation_chain_id: int, temp_messages: list) -> list:
    session_start = time.perf_counter()
    logger.info(f"开始处理本批次消息：{temp_messages}")

    graph = await getVirtualFigureGraph()
    short_term_memory_config = {"configurable": {"thread_id": str(relation_chain_id)}}
    state = initVirtualFigureGraphState(
        {
            "user_id": user_id,
            "relation_chain_id": relation_chain_id,
            "messages_received": temp_messages,
        }
    )
    res: VirtualFigureGraphOutput = await graph.ainvoke(
        state, config=short_term_memory_config
    )

    logger.info(f"处理完成，耗时：{time.perf_counter() - session_start}s\n\n")
    messages_to_send = res["llm_output"].get("messages_to_send", [])
    return messages_to_send


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
        {"relation_chain_id": relation_chain_id, "message": "connected", "index": 0}
    )

    temp_messages = []
    messages_to_process = []
    inactivity_task = {
        "task": None,
        "status": None,
    }  # 最新的scheduleFlush任务

    # 15 秒无新消息触发处理
    async def scheduleFlush():
        try:
            # step 1: 等待 WAITING_SECONDS_FOR_VIRTUAL_FIGURE 秒
            # print("等待阶段")  # todo
            inactivity_task["status"] = "pending"
            await asyncio.sleep(int(os.getenv("WAITING_SECONDS_FOR_VIRTUAL_FIGURE")))
        except asyncio.CancelledError:
            return
        try:
            # step 2: 处理消息
            # print("处理阶段")  # todo
            inactivity_task["status"] = "processing"
            messages_to_process.extend(temp_messages)
            temp_messages.clear()
            messages_to_send = await _processMessages(
                user_id, relation_chain_id, messages_to_process
            )
            messages_to_process.clear()
            # step 3: 发送消息
            inactivity_task["status"] = "sending"
            for item in messages_to_send:
                await websocket.send_json(item)
                await asyncio.sleep(random.randint(8, 22) * 0.1)
            inactivity_task["status"] = "completed"
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

            # 若当前存在正在pending的定时任务，取消当前定时任务，重新开始倒计时
            # 注意：进入处理阶段不可取消，新消息放在清空后的temp_messages中
            if inactivity_task["task"] and inactivity_task["status"] == "pending":
                # print("等待阶段：重新计时")  # todo
                inactivity_task["task"].cancel()
                try:
                    await inactivity_task["task"]
                except asyncio.CancelledError:
                    pass
            inactivity_task["task"] = asyncio.create_task(scheduleFlush())
    finally:
        # 关闭连接时清理定时任务与全局连接状态
        if inactivity_task["task"]:
            inactivity_task["task"].cancel()
            try:
                await inactivity_task["task"]
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


"""HTTP API"""


# 异常处理
@virtual_figure_router.exception
def handleException(error):
    return Response(status_code=500, description=f"error msg: {error}", headers={})


# 鉴权中间件
virtual_figure_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


@virtual_figure_router.post("/recalculateContextBlock")
async def recalculateContextBlock(request: Request) -> dict:
    data = request.json()
    # todo: 删除dev豁免
    user_id = (
        userGetUserIdByAccessToken(request=request)
        if os.getenv("CURRENT_ENV") != "dev"
        else 1
    )
    relation_chain_id = data["relation_chain_id"]
    narrative = data.get("narrative", None)

    res = await vfRecalculateContextBlock(user_id, relation_chain_id, narrative)
    return res


if __name__ == "__main__":

    async def demo(relation_chain_id: int):
        graph = await getVirtualFigureGraph()
        short_term_memory_config = {
            "configurable": {"thread_id": str(relation_chain_id)}
        }
        state1 = initVirtualFigureGraphState(
            {
                "user_id": 1,
                "relation_chain_id": relation_chain_id,
                "messages_received": [
                    {"message": "哈咯", "relation_chain_id": relation_chain_id},
                ],
            }
        )
        session1_start = time.perf_counter()
        res = await graph.ainvoke(state1, config=short_term_memory_config)
        messages_to_send = res["llm_output"].get("messages_to_send", [])
        thinking = res["llm_output"].get("thinking", "")
        print(
            f"session1 耗时：{time.perf_counter() - session1_start}\n\n回复：{messages_to_send}\n\n分析：{thinking}\n"
        )
        # state2 = initVirtualFigureGraphState(
        #     {
        #         "user_id": 1,
        #         "relation_chain_id": relation_chain_id,
        #         "messages_received": [
        #             {
        #                 "message": "你下午去图书馆不",
        #                 "relation_chain_id": relation_chain_id,
        #             },
        #             {
        #                 "message": "我刚吃啥来着？？",
        #                 "relation_chain_id": relation_chain_id,
        #             },
        #         ],
        #     }
        # )
        # session2_start = time.perf_counter()
        # res = await graph.ainvoke(state2, config=short_term_memory_config)
        # print(
        #     f"session2 耗时：{time.perf_counter() - session2_start}\n\n回复：{res}\n\n"
        # )

    asyncio.run(demo(1))
