import json
import os
import logging
from typing import Any, Literal
from sqlalchemy.orm import Session


from database.models import (
    ContextEmbedding,
    Crush,
    Event,
    ChatLog,
    InteractionSignal,
    DerivedInsight,
    Knowledge,
)
from database.enums import EmbeddingType
from agent.index import vectorizeText

logger = logging.getLogger(__name__)


# 构建用于向量化的文本
def buildEmbeddingText(
    content: str | dict,
    summary: str | None = None,
) -> str:
    """
    策略：
    1. 包含 Summary（作为宏观索引）。
    2. 根据内容类型智能追加 Content（作为微观索引）。
    """
    # 构建主体文本
    parts = []
    # 添加摘要 (Summary) - 宏观骨架
    if summary:
        parts.append(f"{summary}")
    # 添加内容 (Content) - 微观血肉
    # 策略：对于字典类型，递归展开关键信息；对于字符串，直接追加。
    if isinstance(content, dict):
        # json复杂结构保留完整键值对语义
        try:
            # ensure_ascii=False 保证中文不被转义，节省 token 且语义更清晰
            content_str = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
            parts.append(f"{content_str}")
        except Exception:
            parts.append(f"{str(content)}")
    elif isinstance(content, str) and content.strip():
        parts.append(f"{content.strip()}")
    else:
        parts.append(f"{str(content)}")
    return "\n".join(parts)


async def createOrUpdateEmbedding(
    db: Session,
    from_where: Literal[
        "knowledge",
        "crush_info",
        "event",
        "chat_log",
        "interaction_signal",
        "derived_insight",
    ],
    knowledge: Knowledge = None,
    cursh: Crush = None,
    event: Event = None,
    chat_log: ChatLog = None,
    interaction_signal: InteractionSignal = None,
    derived_insight: DerivedInsight = None,
) -> dict:
    target_obj = None
    embedding_type = None

    match from_where:
        case "knowledge":
            if not knowledge:
                return {"status": -1, "message": "Knowledge is required"}
            embedding_type = EmbeddingType.FROM_KNOWLEDGE
            # 构建向量化文本
            text = buildEmbeddingText(
                content=knowledge.content,
                summary=knowledge.summary,
            )
        case "crush_info":
            if not cursh:
                return {"status": -1, "message": "Cursh is required"}
            embedding_type = EmbeddingType.FROM_CRUSH_PROFILE
            # 构建向量化文本
            # todo: 需要ai介入
            # parts = []
            # if cursh.name:
            #     parts.append(f"姓名：{cursh.name}")
            # if cursh.gender:
            #     parts.append(f"性别：{cursh.gender.value}")
            # if cursh.mbti:
            #     parts.append(f"MBTI 类型：{cursh.mbti.value}")
            # if cursh.personality_tags:
            #     parts.append(f"性格标签：{', '.join(cursh.personality_tags)}")
            # if cursh.likes:
            #     parts.append(f"喜好：{', '.join(cursh.likes)}")
            # if cursh.dislikes:
            #     parts.append(f"不喜欢：{', '.join(cursh.dislikes)}")
            # if cursh.boundaries:
            #     parts.append(f"个人边界：{', '.join(cursh.boundaries)}")
            # if cursh.traits:
            #     parts.append(f"个人特点：{', '.join(cursh.traits)}")
            # if cursh.other_info:
            #     parts.append(f"{', '.join(cursh.other_info)}")
            # text = buildEmbeddingText(
            #     content="\n".join(parts),
            # )
        case "event":
            if not event:
                return {"status": -1, "message": "Event is required"}
            embedding_type = EmbeddingType.FROM_EVENT
            # 构建向量化文本
            text = buildEmbeddingText(
                content=knowledge.content,
                summary=knowledge.summary,
            )
        case "chat_log":
            if not chat_log:
                return {"status": -1, "message": "Chat_log is required"}
            embedding_type = EmbeddingType.FROM_CHAT_LOG
            # 构建向量化文本
            text = buildEmbeddingText(
                content=knowledge.content,
                summary=knowledge.summary,
            )
        case "interaction_signal":
            if not interaction_signal:
                return {"status": -1, "message": "Interaction_signal is required"}
            embedding_type = EmbeddingType.FROM_INTERACTION_SIGNAL
            # 构建向量化文本
            text = buildEmbeddingText(
                content=knowledge.content,
                summary=knowledge.summary,
            )
        case "derived_insight":
            if not derived_insight:
                return {"status": -1, "message": "Derived_insight is required"}
            embedding_type = EmbeddingType.FROM_DERIVED_INSIGHT
            # 构建向量化文本
            text = buildEmbeddingText(
                content=knowledge.content,
                summary=knowledge.summary,
            )

    logger.info(f"Embedded text: \n{text}")
    # 2. 生成向量
    try:
        vector = await vectorizeText(text)
    except Exception as e:
        return {"status": -2, "message": f"Embedding generation failed: {str(e)}"}

    if not isinstance(vector, list) or not vector:
        return {"status": -3, "message": "Invalid embedding result"}

    # 检查是否存在已有记录
    query = db.query(ContextEmbedding).filter(ContextEmbedding.type == embedding_type)

    match from_where:
        case "knowledge":
            query = query.filter(ContextEmbedding.knowledge_id == knowledge.id)
        # todo：其他情况

    existing = query.first()

    if existing:
        existing.embedding = vector
    else:
        embedding = ContextEmbedding(
            type=embedding_type,
            embedding=vector,
            model_name=os.getenv("EMBEDDING_MODEL_NAME"),
            # 根据来源设置外键
            knowledge_id=knowledge.id if knowledge else None,
            event_id=event.id if event else None,
            chat_log_id=chat_log.id if chat_log else None,
            interaction_signal_id=interaction_signal.id if interaction_signal else None,
            derived_insight_id=derived_insight.id if derived_insight else None,
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
