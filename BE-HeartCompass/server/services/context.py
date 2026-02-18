import json
from sqlalchemy.orm import Session
from typing import Literal

from .ai import summarizeContext
from .embedding import createOrUpdateEmbedding
from database.models import Context, RelationChain, Knowledge
from database.enums import parseEnum, ContextType, ContextSource


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
        json_content = {"text": content}
    summary = await summarizeContext(json.dumps(json_content), "knowledge")

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
        # "knowledge": knowledge.toJson(),
        "embedding": embedding_result,
    }


async def contextAddContext(
    db: Session,
    relation_chain_id: int,
    type: str,
    content: dict | str,
    summary: str | None,
    source: str,
    weight: float,
    confidence: float,
    with_embedding: bool,
) -> dict:
    relation_chain = db.get(RelationChain, relation_chain_id)
    if relation_chain is None:
        return {"status": -1, "message": "Relation chain not found"}

    try:
        context_type = parseEnum(ContextType, type)
    except ValueError:
        return {"status": -2, "message": "Invalid context type"}

    try:
        context_source = parseEnum(ContextSource, source)
    except ValueError:
        return {"status": -3, "message": "Invalid context source"}

    context = Context(
        relation_chain_id=relation_chain_id,
        type=context_type,
        content=content,
        summary=summary,
        source=context_source,
        weight=weight or 1.0,
        confidence=confidence or 1.0,
    )
    db.add(context)
    db.commit()
    db.refresh(context)

    embedding_result = {
        "status": 0,
        "message": "Embedding not created",
    }
    if with_embedding:
        embedding_result = await createOrUpdateEmbedding(
            db, from_where="context", context=context
        )

    return {
        "status": 200,
        "message": "Create context success",
        "context": context.toJson(),
        "embedding": embedding_result,
    }
