"""
todo
"""
# import logging
# import re
# import asyncio

# from src.database.database import session
# from src.database.models import RelationChain, User
# from src.server.services.virtual_figure import vfRecalculateContextBlock

# logger = logging.getLogger(__name__)


# def _sendText2OpenId(open_id: str, text: str) -> None:
#     # 函数内导入，避免循环导入
#     from src.channels.lark.integration.index import sendText2OpenId

#     sendText2OpenId(open_id, text)


# def _getCommonInfo(open_id: str, crush_id: int) -> dict:
#     with session() as db:
#         user = db.query(User).filter(User.lark_open_id == open_id).first()
#         if user is None:
#             logger.warning(f"open_id：{open_id} 未授权")
#             return {}
#         user_id = user.id
#         relation_chain = (
#             db.query(RelationChain)
#             .filter(
#                 RelationChain.user_id == user_id, RelationChain.crush_id == crush_id
#             )
#             .first()
#         )
#         if relation_chain is None:
#             logger.warning(f"不存在关系链")
#             return {}
#         return {
#             "user_id": user_id,
#             "relation_chain_id": relation_chain.id,
#             "crush_name": relation_chain.crush.name,
#         }


# async def _flushContextAndNotify(
#     open_id: str, user_id: int, relation_chain_id: int, crush_id: int
# ) -> None:
#     try:
#         res = await vfRecalculateContextBlock(user_id, relation_chain_id, None)
#     except Exception as e:
#         logger.error(f"刷新上下文失败，person_id={crush_id}，err={e}", exc_info=True)
#         _sendText2OpenId(open_id, f"【System】刷新上下文失败，person_id={crush_id}")
#         return

#     if isinstance(res, dict) and res.get("status", 0) < 0:
#         _sendText2OpenId(
#             open_id,
#             f"【System】刷新上下文失败，person_id={crush_id}，原因：{res.get('message', '未知错误')}",
#         )
#         return

#     _sendText2OpenId(open_id, f"【System】刷新上下文成功，person_id={crush_id}")


# def flushContext(open_id: str, crush_id: int) -> None:
#     common_info = _getCommonInfo(open_id, crush_id)
#     user_id = common_info.get("user_id")
#     relation_chain_id = common_info.get("relation_chain_id")
#     if relation_chain_id is None:
#         _sendText2OpenId(
#             open_id, f"【System】刷新上下文失败，未找到 person_id={crush_id} 对应关系链"
#         )
#         return

#     try:
#         # 检查是否在异步事件循环中
#         asyncio.get_running_loop()
#     except RuntimeError:
#         # 如果不在事件循环中，使用 run 方法启动异步任务
#         logger.info(f"不在事件循环中，使用 run 方法启动异步任务刷新上下文")
#         asyncio.run(
#             _flushContextAndNotify(open_id, user_id, relation_chain_id, crush_id)
#         )
#     else:
#         # 如果在事件循环中，创建新任务
#         logger.info(f"在事件循环中，创建新任务刷新上下文")
#         asyncio.create_task(
#             _flushContextAndNotify(open_id, user_id, relation_chain_id, crush_id)
#         )


# def showMenu(open_id: str) -> None:
#     menu_text = "\n\n".join(
#         [
#             "【System】可用指令：",
#             *[
#                 f"{index}. {item['content']}\n{item['hint']}"
#                 for index, item in enumerate(menu, start=1)
#             ],
#         ]
#     )
#     _sendText2OpenId(open_id, menu_text)


# def listAvailablePersons(open_id: str) -> None:
#     with session() as db:
#         user = db.query(User).filter(User.lark_open_id == open_id).first()
#         if user is None:
#             logger.warning(f"open_id：{open_id} 未授权")
#             return
#         user_id = user.id
#         relation_chains = (
#             db.query(RelationChain).filter(RelationChain.user_id == user_id).all()
#         )
#         if not relation_chains:
#             logger.warning(f"open_id：{open_id} 未绑定任何关系链")
#             return
#         persons_text = "\n".join(
#             [
#                 f"{index}. {rc.crush.name} - person_id: {rc.crush_id}"
#                 for index, rc in enumerate(relation_chains, start=1)
#             ]
#         )
#         _sendText2OpenId(open_id, f"【System】可选对话对象：\n{persons_text}")


# def switchRelationChain(open_id: str, crush_id: int) -> None:
#     from src.channels.lark.integration import index as lark_integration

#     common_info = _getCommonInfo(open_id, crush_id)
#     if common_info.get("relation_chain_id") is None:
#         _sendText2OpenId(
#             open_id, f"【System】切换失败，未找到 crush_id={crush_id} 对应关系链"
#         )
#         return

#     relation_chain_id = common_info.get("relation_chain_id")
#     crush_name = common_info.get("crush_name")

#     with lark_integration._state_lock:
#         lark_integration._active_relation_chain_by_open_id[open_id] = relation_chain_id
#         lark_integration._pending_messages_by_open_id.pop(open_id, None)
#         lark_integration._cancelFlushTimerLocked(open_id)
#     logger.info(
#         f"切换relation_chain成功，relation_chain_id：{relation_chain_id}，crush_name：{crush_name}"
#     )
#     _sendText2OpenId(open_id, f"【System】已切换，当前对话对象为 {crush_name}")


# def clearCurrentRelationChain(open_id: str) -> None:
#     from src.channels.lark.integration import index as lark_integration

#     with lark_integration._state_lock:
#         lark_integration._active_relation_chain_by_open_id.pop(open_id, None)
#         lark_integration._pending_messages_by_open_id.pop(open_id, None)
#         lark_integration._cancelFlushTimerLocked(open_id)
#     logger.info(f"清除relation_chain成功，open_id：{open_id}")
#     _sendText2OpenId(open_id, "【System】已清除当前对话对象")


# def addContextByNarrative(open_id: str, crush_id: int, narrative: str) -> None:
#     _sendText2OpenId(open_id, f"【System】通过自然语言添加上下文暂未实现：{crush_id} {narrative}")


# def addContextByScreenshot(
#     open_id: str,
#     screenshot_url: str,
#     additional_context: str,
#     his_name_or_position_on_screenshot: str,
# ) -> None:
#     _sendText2OpenId(
#         open_id,
#         f"【System】通过聊天记录截图添加上下文暂未实现：{screenshot_url} {additional_context} {his_name_or_position_on_screenshot}",
#     )


# menu = [
#     {
#         "hint": "/list_available_persons",
#         "content": "查找可选对话对象 person_id",
#         "regex": r"/list_available_persons",
#         "command": listAvailablePersons,
#     },
#     {
#         "hint": "/<person_id>",
#         "content": "切换当前对话对象",
#         "regex": r"/(\d+)",
#         "command": switchRelationChain,
#     },
#     {
#         "hint": "/clear_current_person",
#         "content": "清除当前对话对象",
#         "regex": r"/clear_current_person",
#         "command": clearCurrentRelationChain,
#     },
#     # todo：提高优先级，通过单独agent操作落库
#     {
#         "hint": "/add-context-by-narrative:<person_id>\n<narrative>",
#         "content": "通过自然语言添加上下文",
#         "regex": r"/add-context-by-narrative:(\d+)\n(.*)",
#         "command": addContextByNarrative,
#     },
#     # todo：降低优先级，很少需要
#     {
#         "hint": "/add-context-by-screenshot:\n<screenshot>\n<additional_context>\n<his_name_or_position_on_screenshot>",
#         "content": "通过聊天记录截图添加上下文",
#         "regex": r"/add-context-by-screenshot:\n(.*)\n(.*)\n(.*)",
#         "command": addContextByScreenshot,
#     },
#     {
#         "hint": "/flush-context:<person_id>",
#         "content": "刷新关系与画像上下文（添加上下文后请刷新）",
#         "regex": r"/flush-context:(\d+)",
#         "command": flushContext,
#     },
#     {
#         "hint": "/menu",
#         "content": "显示菜单",
#         "regex": r"/menu",
#         "command": showMenu,
#     },
# ]


# def handleMenuCommand(message: str, open_id: str) -> bool:
#     match = None
#     index_hit = None
#     for idx, item in enumerate(menu):
#         match = re.fullmatch(item["regex"], message, re.DOTALL)
#         if not match:
#             continue
#         index_hit = idx
#         break
#     if not match:
#         return False

#     current_item = menu[index_hit]
#     command = current_item["command"]

#     if command == switchRelationChain:
#         command(open_id, int(match.group(1)))
#     elif command == addContextByNarrative:
#         command(open_id, int(match.group(1)), match.group(2))
#     elif command == addContextByScreenshot:
#         command(open_id, match.group(1), match.group(2), match.group(3))
#     elif command == flushContext:
#         command(open_id, int(match.group(1)))
#     elif (
#         command == showMenu
#         or command == listAvailablePersons
#         or command == clearCurrentRelationChain
#     ):
#         command(open_id)
#     else:
#         logger.error(f"未实现的菜单命令：{current_item}")
#         return False
#     return True
