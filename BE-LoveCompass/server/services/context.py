import os
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from langchain_openai import OpenAIEmbeddings

from database.models import Context, ContextEmbedding, RelationChain
from database.enums import parse_enum, ContextType, ContextSource


def _get_embedding_config():
    base_url = os.getenv("ARK_BASE_URL", "")
    model_name = os.getenv("EMBEDDING_MODEL", "") or os.getenv(
        "EMBEDDING_ENDPOINT_ID", ""
    )
    api_key = os.getenv("EMBEDDING_API_KEY", "") or os.getenv("ENDPOINT_API_KEY", "")
    if not model_name:
        model_name = os.getenv("ENDPOINT_ID", "")
    return base_url, model_name, api_key


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


def _create_or_update_embedding(db: Session, context: Context, model_name: str) -> dict:
    base_url, _, api_key = _get_embedding_config()
    if not model_name or not api_key:
        return {"status": "skipped", "reason": "embedding config missing"}

    embedder = OpenAIEmbeddings(model=model_name, api_key=api_key, base_url=base_url)
    text = _build_embedding_text(context.type, context.summary, context.content)
    vector = embedder.embed_query(text)

    if not isinstance(vector, list) or not vector:
        return {"status": "failed", "reason": "invalid embedding result"}

    existing = (
        db.query(ContextEmbedding)
        .filter(
            ContextEmbedding.context_id == context.id,
            ContextEmbedding.model_name == model_name,
        )
        .first()
    )
    if existing:
        existing.embedding = vector
        existing.created_at = datetime.now(timezone.utc)
    else:
        embedding = ContextEmbedding(
            context_id=context.id,
            model_name=model_name,
            embedding=vector,
        )
        db.add(embedding)
    db.commit()
    return {"status": "created", "model_name": model_name}


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

    _, model_name, _ = _get_embedding_config()
    embedding_result = _create_or_update_embedding(db, context, model_name)

    return {
        "status": 200,
        "message": "Create context success",
        "context": context.toJson(),
        "embedding": embedding_result,
    }
