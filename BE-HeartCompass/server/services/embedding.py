import json
import os
from typing import Any, Literal
from sqlalchemy.orm import Session


from database.models import Context, ContextEmbedding, Knowledge
from database.enums import ContextType, EmbeddingType
from agent.index import vectorizeText


# 构建用于向量化的文本
def buildEmbeddingText(
    from_where: Literal["knowledge", "context"],
    category: str | ContextType,
    summary: str | None,
    content: Any,
) -> str:
    """
    策略：
    1. 显式包含类型标签，如 [KNOWLEDGE] 或 [CHAT_LOG]。
    2. 始终包含 Summary（作为宏观索引）。
    3. 根据内容类型智能追加 Content（作为微观索引）。
    """
    # 1. 确定前缀标签
    prefix = ""
    if from_where == "knowledge":
        prefix = "[KNOWLEDGE]"
    elif isinstance(category, ContextType):
        prefix = f"[{category.value.upper()}]"
    else:
        prefix = f"[{str(category).upper()}]"
    # 2. 构建主体文本
    parts = [prefix]
    # 添加摘要 (Summary) - 宏观骨架
    if summary:
        parts.append(f"Summary: {summary}")
    # 添加内容 (Content) - 微观血肉
    # 策略：对于字典类型，递归展开关键信息；对于字符串，直接追加。
    if isinstance(content, dict):
        # 针对 Knowledge 的特殊优化：json复杂结构保留完整键值对语义
        try:
            # ensure_ascii=False 保证中文不被转义，节省 token 且语义更清晰
            content_str = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
            parts.append(f"Content: {content_str}")
        except Exception:
            parts.append(f"Content: {str(content)}")
    elif isinstance(content, str) and content.strip():
        parts.append(f"Content: {content.strip()}")
    else:
        parts.append(f"Content: {str(content)}")
    return "\n".join(parts)


async def createOrUpdateEmbedding(
    db: Session,
    from_where: Literal["knowledge", "context"],
    context: Context = None,
    knowledge: Knowledge = None,
) -> dict:
    target_obj = None
    category = ""
    embedding_type = None

    match from_where:
        case "knowledge":
            if not knowledge:
                return {"status": -1, "message": "Knowledge is required"}
            target_obj = knowledge
            category = "general"  # Knowledge 暂无细分 type, 统一用 general
            embedding_type = EmbeddingType.FROM_KNOWLEDGE
        case "context":
            if not context:
                return {"status": -1, "message": "Context is required"}
            target_obj = context
            category = context.type
            embedding_type = EmbeddingType.FROM_CONTEXT

    # 1. 构建向量化文本
    text = buildEmbeddingText(
        from_where=from_where,
        category=category,
        summary=target_obj.summary,
        content=target_obj.content,
    )
    # 2. 生成向量
    try:
        vector = await vectorizeText(text)
    except Exception as e:
        return {"status": -2, "message": f"Embedding generation failed: {str(e)}"}

    if not isinstance(vector, list) or not vector:
        return {"status": -3, "message": "Invalid embedding result"}

    # 检查是否存在已有记录
    query = db.query(ContextEmbedding).filter(ContextEmbedding.type == embedding_type)

    if from_where == "knowledge":
        query = query.filter(ContextEmbedding.knowledge_id == knowledge.id)
    else:
        query = query.filter(ContextEmbedding.context_id == context.id)

    existing = query.first()

    if existing:
        existing.embedding = vector
    else:
        embedding = ContextEmbedding(
            type=embedding_type,
            embedding=vector,
            model_name=os.getenv("EMBEDDING_MODEL_NAME"),
            # 根据来源设置外键
            knowledge_id=knowledge.id if from_where == "knowledge" else None,
            context_id=context.id if from_where == "context" else None,
        )
        db.add(embedding)
    db.commit()
    return {
        "status": 200,
        "message": "Embedding created",
    }


# todo: 引入weight排序
async def recallEmbedding(
    db: Session,
    text: str,
    top_k: int = 5,
    recall_from: Literal["knowledge", "context", "both"] = "both",
    relation_chain_id: int | None = None,
):
    if not text or not isinstance(text, str) or not text.strip():
        return {"status": -1, "message": "Text is required"}

    if top_k <= 0 or top_k > 20:
        return {"status": -2, "message": "top_k must be between 1 and 20"}

    if recall_from not in {"knowledge", "context", "both"}:
        return {"status": -3, "message": "Invalid recall_from"}

    if recall_from == "context" and relation_chain_id is None:
        return {
            "status": -4,
            "message": "relation_chain_id is required for context recall",
        }

    try:
        vector = await vectorizeText(text)
    except Exception as e:
        return {"status": -5, "message": f"Embedding generation failed: {str(e)}"}

    if not isinstance(vector, list) or not vector:
        return {"status": -6, "message": "Invalid embedding result"}

    items: list[dict[str, Any]] = []
    message_parts: list[str] = []

    if recall_from in {"context", "both"} and relation_chain_id is not None:
        distance = ContextEmbedding.embedding.cosine_distance(vector).label("distance")
        context_query = (
            db.query(ContextEmbedding, distance)
            .filter(ContextEmbedding.type == EmbeddingType.FROM_CONTEXT)
            .join(ContextEmbedding.context)
            .filter(
                Context.is_active.is_(True),
                Context.relation_chain_id == relation_chain_id,
            )
            .order_by(distance.asc())
            .limit(top_k)
        )
        for embedding, dist in context_query.all():
            if not embedding.context:
                continue
            items.append(
                {
                    "source": "context",
                    "embedding_id": embedding.id,
                    "distance": float(dist),
                    "data": embedding.context.toJson(),
                }
            )
    elif recall_from == "both" and relation_chain_id is None:
        message_parts.append("context recall skipped: relation_chain_id missing")

    if recall_from in {"knowledge", "both"}:
        distance = ContextEmbedding.embedding.cosine_distance(vector).label("distance")
        knowledge_query = (
            db.query(ContextEmbedding, distance)
            .filter(ContextEmbedding.type == EmbeddingType.FROM_KNOWLEDGE)
            .join(ContextEmbedding.knowledge)
            .order_by(distance.asc())
            .limit(top_k)
        )
        for embedding, dist in knowledge_query.all():
            if not embedding.knowledge:
                continue
            items.append(
                {
                    "source": "knowledge",
                    "embedding_id": embedding.id,
                    "distance": float(dist),
                    "data": embedding.knowledge.toJson(),
                }
            )

    items.sort(key=lambda x: x["distance"])
    items = items[:top_k]
    message = "Recall embeddings success"
    if message_parts:
        message = f"{message}; " + "; ".join(message_parts)
    return {"status": 200, "message": message, "items": items}
