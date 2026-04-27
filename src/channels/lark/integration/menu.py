import asyncio
import logging
import re
import time
from typing import Literal

from src.agents.graphs.FRBuildingGraph.graph import getFRBuildingGraph
from src.database.index import session
from src.database.models import FigureAndRelation, User
from src.channels.lark.integration.utils import sendCard2OpenId
from src.utils.index import stringifyValue


logger = logging.getLogger(__name__)


def _getCommonInfo(
    open_id: str, fr_id: int
) -> tuple[dict | None, Literal["unauthorized", "fr_not_found"] | None]:
    """
    获取通用信息，包括用户 ID 和 figure 姓名，同时返回错误类型
    """
    with session() as db:
        user = db.query(User).filter(User.lark_open_id == open_id).first()
        if user is None:
            logger.warning(f"open_id：{open_id} is invalid")
            return None, "unauthorized"
        user_id = user.id
        figure_and_relation = (
            db.query(FigureAndRelation)
            .filter(FigureAndRelation.id == fr_id, FigureAndRelation.user_id == user_id)
            .first()
        )
        if figure_and_relation is None:
            logger.warning(f"FR not found")
            return None, "fr_not_found"
        return (
            {
                "user_id": user_id,
                "figure_name": figure_and_relation.figure_name,
            },
            None,
        )


def _submitBackgroundCoroutine(coro: asyncio.coroutines) -> None:
    """
    提交协程到 lark integration 全局异步事件循环后台执行（非阻塞）
    """
    from src.channels.lark.integration import index as lark_integration

    loop = lark_integration._getOrCreateAsyncLoop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)

    def _onDone(fut) -> None:
        try:
            fut.result()
        except Exception as e:
            logger.warning(f"Background coroutine failed: {e}", exc_info=True)

    future.add_done_callback(_onDone)


def showMenu(open_id: str) -> None:
    """
    发送可用指令菜单
    """
    menu_text = "\n\n".join(
        [
            *[
                f"{index}. **{item['content']}**\n```bash\n{item['hint']}\n```"
                for index, item in enumerate(menu, start=1)
            ],
            "发送以上命令即可执行对应操作",
        ]
    )
    sendCard2OpenId(
        open_id=open_id,
        title="Immortality 可用指令",
        content=menu_text,
        theme="turquoise",
    )


def listAvailableFRs(open_id: str) -> None:
    """
    列出可用 FR
    """
    with session() as db:
        user = db.query(User).filter(User.lark_open_id == open_id).first()
        if user is None:
            logger.warning(f"open_id：{open_id} is invalid")
            sendCard2OpenId(
                open_id=open_id,
                title="出错啦",
                content="当前飞书账号未授权，请先绑定账号",
                theme="red",
            )
            return
        user_id = user.id
        figure_and_relations = (
            db.query(FigureAndRelation)
            .filter(FigureAndRelation.user_id == user_id)
            .order_by(FigureAndRelation.id)
            .all()
        )
        if not figure_and_relations or len(figure_and_relations) == 0:
            logger.warning(f"No FR found for this user")
            sendCard2OpenId(
                open_id=open_id,
                title="Immortality 提示",
                content="当前账号未绑定任何对话对象（FR）",
                theme="yellow",
            )
            return
        fr_list = "\n".join(
            [
                f"- **{fr.figure_name}** - {stringifyValue(fr.figure_role).upper()}  \n   `fr_id: {fr.id}`"
                for fr in figure_and_relations
            ]
        )
        sendCard2OpenId(
            open_id=open_id,
            title="可选对话对象",
            content=f"请选择要切换的对象：\n\n{fr_list}\n\n发送 `/<fr_id>` 即可切换",
            theme="turquoise",
        )


def switchFR(open_id: str, fr_id: int) -> None:
    """
    切换 FR
    """
    from src.channels.lark.integration import index as lark_integration

    common_info, error_type = _getCommonInfo(open_id, fr_id)
    if common_info is None:
        if error_type == "unauthorized":
            sendCard2OpenId(
                open_id=open_id,
                title="出错啦",
                content="当前飞书账号未授权，请先绑定账号",
                theme="red",
            )
            return
        sendCard2OpenId(
            open_id=open_id,
            title="出错啦",
            content=f"切换失败：未找到 `fr_id={fr_id}` 对应的对话对象",
            theme="red",
        )
        return

    figure_name = common_info.get("figure_name")

    with lark_integration._state_lock:
        # 更新当前激活的 openid-fr_id 映射
        lark_integration._active_fr_by_open_id[open_id] = fr_id
        # 清空待处理的消息队列
        lark_integration._pending_messages_by_open_id.pop(open_id, None)
        # 取消计时器
        lark_integration._cancelFlushTimerLocked(open_id)
    logger.info(f"Successfully switch FR to {figure_name}")
    sendCard2OpenId(
        open_id=open_id,
        title="对话人切换成功",
        content=f"我是 **{figure_name}**",
        theme="green",
    )


def clearCurrentRelationChain(open_id: str) -> None:
    """
    清除当前对话对象
    """
    from src.channels.lark.integration import index as lark_integration

    with lark_integration._state_lock:
        lark_integration._active_fr_by_open_id.pop(open_id, None)
        lark_integration._pending_messages_by_open_id.pop(open_id, None)
        lark_integration._cancelFlushTimerLocked(open_id)
    logger.info(f"Successfully clear FR for {open_id}")
    sendCard2OpenId(
        open_id=open_id,
        title="清除成功",
        content="已清除当前对话对象",
        theme="green",
    )


def buildPersona(open_id: str, fr_id: int, text: str) -> None:
    """
    完善 / 补充人物画像
    """
    common_info, error_type = _getCommonInfo(open_id, fr_id)
    if common_info is None:
        if error_type == "unauthorized":
            sendCard2OpenId(
                open_id=open_id,
                title="出错啦",
                content="当前飞书账号未授权，请先绑定账号",
                theme="red",
            )
            return
        sendCard2OpenId(
            open_id=open_id,
            title="出错啦",
            content=f"完善人物画像失败：未找到 `fr_id={fr_id}` 对应的对话对象",
            theme="red",
        )
        return

    user_id = common_info.get("user_id")
    figure_name = common_info.get("figure_name")
    sendCard2OpenId(
        open_id=open_id,
        title="任务开始",
        content=f"开始完善 **{figure_name}** 的人物画像，完成后会通知结果",
        theme="blue",
    )

    async def _task() -> None:
        """
        完善人物画像任务
        """
        start_time = time.perf_counter()
        try:
            graph = getFRBuildingGraph()
            init_state = {
                "request": {
                    "user_id": user_id,
                    "fr_id": fr_id,
                    "raw_content": text,
                    # "raw_images": [],
                },
            }
            await graph.ainvoke(init_state)
            end_time = time.perf_counter()
            logger.info(f"Successfully build persona for {figure_name}")
            sendCard2OpenId(
                open_id=open_id,
                title="人物画像完善成功",
                content=f"已完成 **{figure_name}** 人物画像完善，耗时 `{end_time - start_time:.2f}s`",
                theme="green",
            )
        except Exception as e:
            logger.warning(
                f"Fail to build persona, open_id={open_id}, fr_id={fr_id}, err={e}",
                exc_info=True,
            )
            sendCard2OpenId(
                open_id=open_id,
                title="出错啦",
                content="完善人物画像失败，请稍后重试",
                theme="red",
            )

    # 提交到后台异步 loop 执行，不阻塞当前消息处理链路
    _submitBackgroundCoroutine(_task())


menu = [
    {
        "hint": "/menu",
        "content": "显示菜单",
        "regex": r"/menu",
        "command": showMenu,
    },
    {
        "hint": "/list_available_persons",
        "content": "查找全部对话对象 fr_id",
        "regex": r"/list_available_persons",
        "command": listAvailableFRs,
    },
    {
        "hint": "/<fr_id>",
        "content": "切换当前对话对象",
        "regex": r"/(\d+)",
        "command": switchFR,
    },
    {
        "hint": "/clear_current_person",
        "content": "清除当前对话对象",
        "regex": r"/clear_current_person",
        "command": clearCurrentRelationChain,
    },
    {
        "hint": "/build_persona:<fr_id>\n<text>",
        "content": "完善 / 补充人物画像（可添加你对对方的文字表述、对方主笔长文（博客、日记、笔记等）、聊天记录、社交表达、创作物等）",
        "regex": r"/build_persona:(\d+)\n(.*)",
        "command": buildPersona,
    },
]


def handleMenuCommand(message: str, open_id: str) -> bool:
    """
    处理 / 开头的菜单命令
    """
    match = None
    index_hit = None
    for idx, item in enumerate(menu):
        match = re.fullmatch(item["regex"], message, re.DOTALL)
        if not match:
            continue
        index_hit = idx
        break
    if not match:
        return False

    current_item = menu[index_hit]
    command = current_item["command"]

    if command == switchFR:
        command(open_id, int(match.group(1)))
    elif command == buildPersona:
        command(open_id, int(match.group(1)), match.group(2))
    elif (
        command == showMenu
        or command == listAvailableFRs
        or command == clearCurrentRelationChain
    ):
        command(open_id)
    else:
        logger.error(f"Unsupported command: {command}")
        return False
    return True
