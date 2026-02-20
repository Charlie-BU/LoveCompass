import json
import logging
from sqlalchemy.orm import Session
from typing import Literal

from .ai import summarizeContext, extractKnowledge, normalizeContext
from .embedding import createOrUpdateEmbedding
from database.models import RelationChain, Knowledge
from database.enums import parseEnum

logger = logging.getLogger(__name__)


async def contextAddKnowledge(
    db: Session,
    content: str,
    with_embedding: bool,
) -> dict:
    try:
        knowledges = json.loads(await extractKnowledge(content))
    except Exception as e:
        return {"status": -1, "message": f"Failed to extract knowledge: {e}"}

    if not isinstance(knowledges, list):
        return {"status": -1, "message": "Failed to extract knowledge: invalid format"}

    logger.info(f"Extracted knowledge: \n{json.dumps(knowledges, indent=4)}")

    if len(knowledges) == 0:
        return {
            "status": -2,
            "message": "No knowledge extracted",
        }

    knowledge_items: list[Knowledge] = []
    try:
        transaction_ctx = db.begin_nested() if db.in_transaction() else db.begin()
        with transaction_ctx:
            for idx, item in enumerate(knowledges):
                if not isinstance(item, dict):
                    return {
                        "status": -3,
                        "message": f"Invalid knowledge item at index {idx}",
                    }
                item_content = item.get("content")
                item_summary = item.get("summary")
                item_weight = item.get("weight")
                if not isinstance(item_content, str) or item_content.strip() == "":
                    return {
                        "status": -4,
                        "message": f"Invalid content at index {idx}",
                    }
                if item_summary is not None and not isinstance(item_summary, str):
                    return {
                        "status": -5,
                        "message": f"Invalid summary at index {idx}",
                    }
                if not isinstance(item_weight, (int, float)) or not (
                    0 <= float(item_weight) <= 1
                ):
                    return {
                        "status": -6,
                        "message": f"Invalid weight at index {idx}",
                    }
                knowledge = Knowledge(
                    content=item_content,
                    weight=float(item_weight),
                    summary=item_summary,
                )
                db.add(knowledge)
                knowledge_items.append(knowledge)
            db.flush()
    except Exception as e:
        return {"status": -7, "message": f"Error saving knowledge: {e}"}

    for knowledge in knowledge_items:
        db.refresh(knowledge)

    embedding_result = []
    if with_embedding:
        for knowledge in knowledge_items:
            embedding_result.append(
                await createOrUpdateEmbedding(
                    db=db, from_where="knowledge", knowledge=knowledge
                )
            )

    return {
        "status": 200,
        "message": "Knowledge added",
        "count": len(knowledge_items),
        "knowledge_ids": [item.id for item in knowledge_items],
        "embedding": embedding_result,
    }


# todo：按照新架构重写
# async def contextAddContextByNaturalLanguage(
#     db: Session,
#     relation_chain_id: int,
#     content: str,
#     weight: float,
#     with_embedding: bool,
# ) -> dict:
#     relation_chain = db.get(RelationChain, relation_chain_id)
#     if relation_chain is None:
#         return {"status": -1, "message": "Relation chain not found"}
#     if not content or content.strip() == "":
#         return {"status": -2, "message": "Content is empty"}

#     try:
#         normalized_context = json.loads(await normalizeContext(content))
#     except json.JSONDecodeError:
#         return {"status": -3, "message": "Failed to normalize context"}

#     if not isinstance(normalized_context, dict):
#         return {"status": -3, "message": "Failed to normalize context"}

#     # logger.info("normalized_context=%s", normalized_context)    # 生产环境记得注释掉

#     STATIC_PROFILE = normalized_context.get("STATIC_PROFILE")
#     STAGE_EVENT = normalized_context.get("STAGE_EVENT")
#     if STATIC_PROFILE is None and STAGE_EVENT is None:
#         return {"status": -4, "message": "No valid context found"}

#     if STATIC_PROFILE is not None and not isinstance(STATIC_PROFILE, dict):
#         return {"status": -5, "message": "Invalid STATIC_PROFILE format"}
#     if STAGE_EVENT is not None and not isinstance(STAGE_EVENT, dict):
#         return {"status": -6, "message": "Invalid STAGE_EVENT format"}

#     safe_weight = weight if weight is not None else 1.0
#     new_context_STATIC_PROFILE = None
#     new_context_STAGE_EVENT = None

#     summary_STATIC_PROFILE = None
#     stage_STAGE_EVENT = None
#     if STATIC_PROFILE is not None:
#         try:
#             summary_STATIC_PROFILE = await summarizeContext(
#                 json.dumps(STATIC_PROFILE), "context"
#             )
#         except Exception as e:
#             return {"status": -7, "message": f"Error summarizing context: {e}"}

#     if STAGE_EVENT is not None:
#         stage_STAGE_EVENT = STAGE_EVENT.get("summary")
#         if stage_STAGE_EVENT is None:
#             try:
#                 stage_STAGE_EVENT = await summarizeContext(
#                     json.dumps(STAGE_EVENT), "context"
#                 )
#             except Exception as e:
#                 return {"status": -7, "message": f"Error summarizing context: {e}"}

#     try:
#         # 使用事务一次性写入两类 Context，避免部分成功导致数据不一致
#         transaction_ctx = db.begin_nested() if db.in_transaction() else db.begin()
#         with transaction_ctx:
#             if STATIC_PROFILE is not None:
#                 new_context_STATIC_PROFILE = Context(
#                     relation_chain_id=relation_chain_id,
#                     type=ContextType.STATIC_PROFILE,
#                     content=STATIC_PROFILE,
#                     summary=summary_STATIC_PROFILE,
#                     weight=safe_weight,
#                     confidence=1.0,
#                 )
#                 db.add(new_context_STATIC_PROFILE)
#             if STAGE_EVENT is not None:
#                 new_context_STAGE_EVENT = Context(
#                     relation_chain_id=relation_chain_id,
#                     type=ContextType.STAGE_EVENT,
#                     content=STAGE_EVENT,
#                     summary=stage_STAGE_EVENT,
#                     weight=safe_weight,
#                     confidence=1.0,
#                 )
#                 db.add(new_context_STAGE_EVENT)
#             db.flush()
#     except Exception as e:
#         return {"status": -8, "message": f"Error saving context: {e}"}

#     if new_context_STATIC_PROFILE is not None:
#         db.refresh(new_context_STATIC_PROFILE)
#     if new_context_STAGE_EVENT is not None:
#         db.refresh(new_context_STAGE_EVENT)

#     embedding_result_STATIC_PROFILE = None
#     embedding_result_STAGE_EVENT = None
#     if new_context_STATIC_PROFILE is not None:
#         embedding_result_STATIC_PROFILE = {
#             "status": 0,
#             "message": "Embedding not created",
#         }
#         if with_embedding:
#             embedding_result_STATIC_PROFILE = await createOrUpdateEmbedding(
#                 db, from_where="context", context=new_context_STATIC_PROFILE
#             )

#     if new_context_STAGE_EVENT is not None:
#         embedding_result_STAGE_EVENT = {
#             "status": 0,
#             "message": "Embedding not created",
#         }
#         if with_embedding:
#             embedding_result_STAGE_EVENT = await createOrUpdateEmbedding(
#                 db, from_where="context", context=new_context_STAGE_EVENT
#             )
#     embedding_result = {}
#     if embedding_result_STATIC_PROFILE is not None:
#         embedding_result["STATIC_PROFILE"] = embedding_result_STATIC_PROFILE
#     if embedding_result_STAGE_EVENT is not None:
#         embedding_result["STAGE_EVENT"] = embedding_result_STAGE_EVENT
#     return {
#         "status": 200,
#         "message": "Create context success",
#         "normalized_context": normalized_context,
#         "embedding": embedding_result,
#     }


# todo: 按type分别存
# async def contextAddContext(
#     db: Session,
#     relation_chain_id: int,
#     type: str,
#     content: dict | str,
#     summary: str | None,
#     weight: float,
#     confidence: float,
#     with_embedding: bool,
# ) -> dict:
#     relation_chain = db.get(RelationChain, relation_chain_id)
#     if relation_chain is None:
#         return {"status": -1, "message": "Relation chain not found"}

#     try:
#         context_type = parseEnum(ContextType, type)
#     except ValueError:
#         return {"status": -2, "message": "Invalid context type"}

#     context = Context(
#         relation_chain_id=relation_chain_id,
#         type=context_type,
#         content=content,
#         summary=summary,
#         weight=weight or 1.0,
#         confidence=confidence or 1.0,
#     )
#     db.add(context)
#     db.commit()
#     db.refresh(context)

#     embedding_result = {
#         "status": 0,
#         "message": "Embedding not created",
#     }
#     if with_embedding:
#         embedding_result = await createOrUpdateEmbedding(
#             db, from_where="context", context=context
#         )

#     return {
#         "status": 200,
#         "message": "Create context success",
#         "context": context.toJson(),
#         "embedding": embedding_result,
#     }
