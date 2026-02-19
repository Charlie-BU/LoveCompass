import json
import logging
from sqlalchemy.orm import Session
from typing import Literal

from .ai import summarizeContext, normalizeContext
from .embedding import createOrUpdateEmbedding
from database.models import Context, RelationChain, Knowledge
from database.enums import parseEnum, ContextType

logger = logging.getLogger(__name__)


async def contextAddKnowledge(
    db: Session,
    content: str,
    weight: float,
    with_embedding: bool,
) -> dict:
    if weight < 0 or weight > 1:
        return {"status": -1, "message": "Weight must be between 0 and 1"}
    try:
        json_content = json.loads(content)
        if not isinstance(json_content, dict):
            json_content = {"content": json_content}
    except json.JSONDecodeError:
        json_content = {"content": content}
    try:
        summary = await summarizeContext(json.dumps(json_content), "knowledge")
    except Exception as e:
        return {"status": -2, "message": f"Error summarizing context: {e}"}

    knowledge = Knowledge(
        content=json_content,
        weight=weight,
        summary=summary,
    )
    db.add(knowledge)
    db.commit()
    db.refresh(knowledge)

    embedding_result = {
        "status": 0,
        "message": "Embedding not created",
    }
    if with_embedding:
        embedding_result = await createOrUpdateEmbedding(
            db, from_where="knowledge", knowledge=knowledge
        )

    return {
        "status": 200,
        "message": "Knowledge added",
        "embedding": embedding_result,
    }


# todo：太慢，寻找优化方向？
async def contextAddContextByNaturalLanguage(
    db: Session,
    relation_chain_id: int,
    content: str,
    weight: float,
    with_embedding: bool,
) -> dict:
    relation_chain = db.get(RelationChain, relation_chain_id)
    if relation_chain is None:
        return {"status": -1, "message": "Relation chain not found"}
    if not content or content.strip() == "":
        return {"status": -2, "message": "Content is empty"}
        
    try:
        normalized_context = json.loads(await normalizeContext(content))
    except json.JSONDecodeError:
        return {"status": -3, "message": "Failed to normalize context"}

    if not isinstance(normalized_context, dict):
        return {"status": -3, "message": "Failed to normalize context"}

    # logger.info("normalized_context=%s", normalized_context)    # 生产环境记得注释掉

    STATIC_PROFILE = normalized_context.get("STATIC_PROFILE")
    STAGE_EVENT = normalized_context.get("STAGE_EVENT")
    if STATIC_PROFILE is None and STAGE_EVENT is None:
        return {"status": -4, "message": "No valid context found"}

    if STATIC_PROFILE is not None and not isinstance(STATIC_PROFILE, dict):
        return {"status": -5, "message": "Invalid STATIC_PROFILE format"}
    if STAGE_EVENT is not None and not isinstance(STAGE_EVENT, dict):
        return {"status": -6, "message": "Invalid STAGE_EVENT format"}

    safe_weight = weight if weight is not None else 1.0
    new_context_STATIC_PROFILE = None
    new_context_STAGE_EVENT = None

    summary_STATIC_PROFILE = None
    stage_STAGE_EVENT = None
    if STATIC_PROFILE is not None:
        try:
            summary_STATIC_PROFILE = await summarizeContext(
                json.dumps(STATIC_PROFILE), "context"
            )
        except Exception as e:
            return {"status": -7, "message": f"Error summarizing context: {e}"}

    if STAGE_EVENT is not None:
        stage_STAGE_EVENT = STAGE_EVENT.get("summary")
        if stage_STAGE_EVENT is None:
            try:
                stage_STAGE_EVENT = await summarizeContext(
                    json.dumps(STAGE_EVENT), "context"
                )
            except Exception as e:
                return {"status": -7, "message": f"Error summarizing context: {e}"}

    try:
        # 使用事务一次性写入两类 Context，避免部分成功导致数据不一致
        transaction_ctx = db.begin_nested() if db.in_transaction() else db.begin()
        with transaction_ctx:
            if STATIC_PROFILE is not None:
                new_context_STATIC_PROFILE = Context(
                    relation_chain_id=relation_chain_id,
                    type=ContextType.STATIC_PROFILE,
                    content=STATIC_PROFILE,
                    summary=summary_STATIC_PROFILE,
                    weight=safe_weight,
                    confidence=1.0,
                )
                db.add(new_context_STATIC_PROFILE)
            if STAGE_EVENT is not None:
                new_context_STAGE_EVENT = Context(
                    relation_chain_id=relation_chain_id,
                    type=ContextType.STAGE_EVENT,
                    content=STAGE_EVENT,
                    summary=stage_STAGE_EVENT,
                    weight=safe_weight,
                    confidence=1.0,
                )
                db.add(new_context_STAGE_EVENT)
            db.flush()
    except Exception as e:
        return {"status": -8, "message": f"Error saving context: {e}"}

    if new_context_STATIC_PROFILE is not None:
        db.refresh(new_context_STATIC_PROFILE)
    if new_context_STAGE_EVENT is not None:
        db.refresh(new_context_STAGE_EVENT)

    embedding_result_STATIC_PROFILE = None
    embedding_result_STAGE_EVENT = None
    if new_context_STATIC_PROFILE is not None:
        embedding_result_STATIC_PROFILE = {
            "status": 0,
            "message": "Embedding not created",
        }
        if with_embedding:
            embedding_result_STATIC_PROFILE = await createOrUpdateEmbedding(
                db, from_where="context", context=new_context_STATIC_PROFILE
            )

    if new_context_STAGE_EVENT is not None:
        embedding_result_STAGE_EVENT = {
            "status": 0,
            "message": "Embedding not created",
        }
        if with_embedding:
            embedding_result_STAGE_EVENT = await createOrUpdateEmbedding(
                db, from_where="context", context=new_context_STAGE_EVENT
            )
    embedding_result = {}
    if embedding_result_STATIC_PROFILE is not None:
        embedding_result["STATIC_PROFILE"] = embedding_result_STATIC_PROFILE
    if embedding_result_STAGE_EVENT is not None:
        embedding_result["STAGE_EVENT"] = embedding_result_STAGE_EVENT
    return {
        "status": 200,
        "message": "Create context success",
        "normalized_context": normalized_context,
        "embedding": embedding_result,
    }


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
