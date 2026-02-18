import json
import os
from typing import Any, Literal
from sqlalchemy.orm import Session


from agent.index import vectorizeText
from database.models import Context, ContextEmbedding, Knowledge
from database.enums import ContextType, EmbeddingType


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
