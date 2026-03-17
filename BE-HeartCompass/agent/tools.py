# from typing import Annotated
# from langchain_core.tools import tool

# from database.database import session

# @tool
# async def recallNonKnowledge(query: Annotated[str, "Key words for non-knowledge recall"]) -> str:
#     """Recall event, chat_topic, derived_insight related to the query"""
#     try:
#         with session() as db:
#             res = await recallEmbeddingFromDB(
#                 db=db,
#                 text=query,
#                 top_k=30,
#                 recall_from=["event", "chat_topic", "derived_insight"],
#                 relation_chain_id=request.get("relation_chain_id"),
#             )
#             if res["status"] == 200:
#                 recalled_items = res["items"]
#                 for item in recalled_items:
#                     match item["source"]:
#                         case "event":
#                             events.append(item["data"])
#                         case "chat_topic":
#                             chat_topics.append(item["data"])
#                         case "derived_insight":
#                             derived_insights.append(item["data"])
#             else:
#                 logger.warning(f"Error recalling non-knowledge items: {res}")

#     except Exception as e:
#         return f"Error: {str(e)}"
