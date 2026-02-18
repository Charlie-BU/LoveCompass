import json
from datetime import datetime, timezone
from typing import Any, Literal
from sqlalchemy.orm import Session


from .ai import summarize_context
from agent.index import get_embedder
from database.models import Context, ContextEmbedding, RelationChain, Knowledge
from database.enums import parse_enum, ContextType, ContextSource


# todo：逻辑需要再确认
def _build_embedding_text(
    context_type: ContextType, summary: str | None, content: Any
) -> str:
    if summary:
        return f"[{context_type.value}] {summary}"
    if isinstance(content, str):
        return f"[{context_type.value}] {content}"
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str) and text.strip():
            return f"[{context_type.value}] {text}"
        parts = []
        for key, value in content.items():
            parts.append(f"{key}: {value}")
        return f"[{context_type.value}] " + "; ".join(parts)
    return f"[{context_type.value}] {str(content)}"


def _create_or_update_embedding(
    db: Session, from_where: Literal["knowledge", "context"], context: Context
) -> dict:
    embedder = get_embedder()
    # 1. 准备文本：把 context 的类型、摘要、内容拼成一个完整的字符串。
    text = _build_embedding_text(context.type, context.summary, context.content)
    # 2. 生成向量：调用远程 AI 接口，把文本变成向量（如 [0.01, -0.2, ...]）。
    vector = embedder.embed_query(text)

    if not isinstance(vector, list) or not vector:
        return {"status": -1, "message": "invalid embedding result"}

    existing = (
        db.query(ContextEmbedding)
        .filter(
            ContextEmbedding.context_id == context.id,
        )
        .first()
    )
    if existing:
        existing.embedding = vector
    else:
        embedding = ContextEmbedding(
            context_id=context.id,
            embedding=vector,
        )
        db.add(embedding)
    db.commit()
    return {
        "status": 200,
        "message": "embedding created",
    }


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
    summary = await summarize_context(json.dumps(json_content), "knowledge")

    knowledge = Knowledge(
        content=json_content,
        weight=weight,
        summary=summary,
    )
    db.add(knowledge)
    db.commit()
    return {
        "status": 200,
        "message": "Knowledge added",
        "knowledge": knowledge.toJson(),
    }


def contextCreateWithEmbedding(
    db: Session,
    relation_chain_id: int,
    type: str,
    content: dict | str,
    summary: str | None,
    source: str,
    weight: float | None = 1.0,
    confidence: float | None = 1.0,
    derived_from_context_id: int | None = None,
) -> dict:
    relation_chain = db.get(RelationChain, relation_chain_id)
    if relation_chain is None:
        return {"status": -1, "message": "Relation chain not found"}

    try:
        context_type = parse_enum(ContextType, type)
    except ValueError:
        return {"status": -2, "message": "Invalid context type"}

    try:
        context_source = parse_enum(ContextSource, source)
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
        derived_from_context_id=derived_from_context_id,
    )
    db.add(context)
    db.commit()
    db.refresh(context)

    embedding_result = _create_or_update_embedding(db, context)

    return {
        "status": 200,
        "message": "Create context success",
        "context": context.toJson(),
        "embedding": embedding_result,
    }
