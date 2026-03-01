import json
import os
import logging
from typing import Any, List, Literal
from sqlalchemy.orm import Session


from database.models import (
    ContextEmbedding,
    Crush,
    Event,
    ChatTopic,
    DerivedInsight,
    Knowledge,
    RelationChain,
)
from database.enums import EmbeddingType
from agent.embedding import vectorizeText
from utils import cleanList


logger = logging.getLogger(__name__)


def buildEmbeddingText4Knowledge(
    knowledge: Knowledge,
) -> str:
    """
    策略：
    1. 包含 Summary（作为宏观索引）。
    2. 根据内容类型智能追加 Content（作为微观索引）。
    """
    # 构建主体文本
    parts = []
    # 添加摘要 (Summary) - 宏观骨架
    if knowledge.summary:
        parts.append(f"{knowledge.summary}")
    # 添加内容 (Content) - 微观血肉
    # 策略：对于字典类型，递归展开关键信息；对于字符串，直接追加。
    if isinstance(knowledge.content, dict):
        # json复杂结构保留完整键值对语义
        try:
            # ensure_ascii=False 保证中文不被转义，节省 token 且语义更清晰
            content_str = json.dumps(
                knowledge.content, ensure_ascii=False, separators=(",", ":")
            )
            parts.append(f"{content_str}")
        except Exception:
            parts.append(f"{str(knowledge.content)}")
    elif isinstance(knowledge.content, str) and knowledge.content.strip():
        parts.append(f"{knowledge.content.strip()}")
    else:
        parts.append(f"{str(knowledge.content)}")
    return "\n".join(parts)


def buildEmbeddingText4CrushProfile(
    crush: Crush,
) -> str:
    parts = []
    if crush.name:
        parts.append(f"姓名：{crush.name}")
    if crush.gender:
        parts.append(f"性别：{crush.gender.value}")
    if crush.mbti:
        parts.append(f"MBTI 类型: {crush.mbti.value}")
    if crush.birthday:
        parts.append(f"生日/星座: {crush.birthday}")
    if crush.occupation:
        parts.append(f"职业: {crush.occupation}")
    if crush.education:
        parts.append(f"教育背景: {crush.education}")
    if crush.residence:
        parts.append(f"常住地: {crush.residence}")
    if crush.hometown:
        parts.append(f"家乡: {crush.hometown}")
    communication_style = cleanList(crush.communication_style)
    if communication_style:
        parts.append(f"沟通风格: {', '.join(communication_style)}")

    personality_tags = cleanList(crush.personality_tags)
    if personality_tags:
        parts.append(f"性格标签: {', '.join(personality_tags)}")

    likes = cleanList(crush.likes)
    if likes:
        parts.append(f"喜好: {', '.join(likes)}")

    dislikes = cleanList(crush.dislikes)
    if dislikes:
        parts.append(f"不喜欢: {', '.join(dislikes)}")

    boundaries = cleanList(crush.boundaries)
    if boundaries:
        parts.append(f"个人边界: {', '.join(boundaries)}")

    traits = cleanList(crush.traits)
    if traits:
        parts.append(f"个人特点: {', '.join(traits)}")

    lifestyle_tags = cleanList(crush.lifestyle_tags)
    if lifestyle_tags:
        parts.append(f"生活方式: {', '.join(lifestyle_tags)}")

    values = cleanList(crush.values)
    if values:
        parts.append(f"价值观: {', '.join(values)}")

    appearance_tags = cleanList(crush.appearance_tags)
    if appearance_tags:
        parts.append(f"外在特征: {', '.join(appearance_tags)}")

    if crush.other_info:
        other_info_parts = []
        for item in crush.other_info:
            if isinstance(item, dict):
                other_info_parts.append(
                    json.dumps(item, ensure_ascii=False, sort_keys=True)
                )
            elif isinstance(item, str) and item.strip():
                other_info_parts.append(item.strip())
        if other_info_parts:
            parts.append(f"其他信息: {', '.join(other_info_parts)}")

    return "\n".join(parts)


def buildEmbeddingText4Event(
    event: Event,
) -> str:
    parts = ["事件"]
    if event.summary:
        parts.append(f"{event.summary}")
    if event.content:
        parts.append(f"{event.content}")
    if event.date:
        parts.append(f"{event.date}")
    if event.other_info:
        other_info_parts = []
        for item in event.other_info:
            if isinstance(item, dict):
                other_info_parts.append(
                    json.dumps(item, ensure_ascii=False, sort_keys=True)
                )
            elif isinstance(item, str) and item.strip():
                other_info_parts.append(item.strip())
        if other_info_parts:
            parts.append(f"其他信息: {', '.join(other_info_parts)}")
    return "\n".join(parts)


def buildEmbeddingText4ChatTopic(
    chat_topic: ChatTopic,
) -> str:
    parts = ["聊天话题"]
    if chat_topic.title:
        parts.append(f"{chat_topic.title}")
    if chat_topic.summary:
        parts.append(f"{chat_topic.summary}")
    if chat_topic.content:
        parts.append(f"{chat_topic.content}")
    if chat_topic.topic_time:
        time_value = str(chat_topic.topic_time).strip()
        if time_value:
            parts.append(f"{time_value}")
    if chat_topic.channel:
        parts.append(f"{chat_topic.channel.value}")
    if chat_topic.attitude:
        parts.append(f"{chat_topic.attitude.value}")
    tags = cleanList(chat_topic.tags)
    if tags:
        parts.append(f"话题标签: {', '.join(tags)}")
    participants = cleanList(chat_topic.participants)
    if participants:
        parts.append(f"参与者: {', '.join(participants)}")
    if chat_topic.other_info:
        other_info_parts = []
        for item in chat_topic.other_info:
            if isinstance(item, dict):
                other_info_parts.append(
                    json.dumps(item, ensure_ascii=False, sort_keys=True)
                )
            elif isinstance(item, str) and item.strip():
                other_info_parts.append(item.strip())
        if other_info_parts:
            parts.append(f"其他信息: {', '.join(other_info_parts)}")
    return "\n".join(parts)


def buildEmbeddingText4DerivedInsight(
    derived_insight: DerivedInsight,
) -> str:
    parts = ["洞察"]
    if derived_insight.insight:
        parts.append(f"{derived_insight.insight}")
    if derived_insight.additional_info:
        additional_info_parts = []
        for item in derived_insight.additional_info:
            if isinstance(item, dict):
                additional_info_parts.append(
                    json.dumps(item, ensure_ascii=False, sort_keys=True)
                )
            elif isinstance(item, str) and item.strip():
                additional_info_parts.append(item.strip())
        if additional_info_parts:
            parts.append(f"其他信息: {', '.join(additional_info_parts)}")
    return "\n".join(parts)


async def createOrUpdateEmbedding(
    db: Session,
    from_where: Literal[
        "knowledge",
        "crush_profile",
        "event",
        "chat_topic",
        "derived_insight",
    ],
    knowledge: Knowledge = None,
    crush: Crush = None,
    event: Event = None,
    chat_topic: ChatTopic = None,
    derived_insight: DerivedInsight = None,
) -> dict:
    embedding_type = None
    text = None

    match from_where:
        case "knowledge":
            if not knowledge:
                return {"status": -1, "message": "Knowledge is required"}
            embedding_type = EmbeddingType.FROM_KNOWLEDGE
            # 构建向量化文本
            text = buildEmbeddingText4Knowledge(knowledge)
        case "crush_profile":
            if not crush:
                return {"status": -1, "message": "Crush is required"}
            embedding_type = EmbeddingType.FROM_CRUSH_PROFILE
            # 构建向量化文本
            text = buildEmbeddingText4CrushProfile(crush)
        case "event":
            if not event:
                return {"status": -1, "message": "Event is required"}
            embedding_type = EmbeddingType.FROM_EVENT
            # 构建向量化文本
            text = buildEmbeddingText4Event(event)
        case "chat_topic":
            if not chat_topic:
                return {"status": -1, "message": "Chat_topic is required"}
            embedding_type = EmbeddingType.FROM_CHAT_TOPIC
            # 构建向量化文本
            text = buildEmbeddingText4ChatTopic(chat_topic)
        case "derived_insight":
            if not derived_insight:
                return {"status": -1, "message": "Derived_insight is required"}
            embedding_type = EmbeddingType.FROM_DERIVED_INSIGHT
            # 构建向量化文本
            text = buildEmbeddingText4DerivedInsight(derived_insight)

    if not text:
        return {"status": -2, "message": "Embedding text is empty"}

    logger.info(f"Embedded text: \n{text}")
    # 生成向量
    try:
        vector = await vectorizeText(text)
    except Exception as e:
        return {"status": -3, "message": f"Embedding generation failed: {str(e)}"}

    if not isinstance(vector, list) or not vector:
        return {"status": -4, "message": "Invalid embedding result"}

    # 检查是否存在已有记录
    query = None
    match from_where:
        case "knowledge":
            query = db.query(ContextEmbedding).filter(
                ContextEmbedding.type == embedding_type,
                ContextEmbedding.knowledge_id == knowledge.id,
            )
        case "crush_profile":
            query = db.query(ContextEmbedding).filter(
                ContextEmbedding.type == embedding_type,
                ContextEmbedding.crush_id == crush.id,
            )
        case "event":
            query = db.query(ContextEmbedding).filter(
                ContextEmbedding.type == embedding_type,
                ContextEmbedding.event_id == event.id,
            )
        case "chat_topic":
            query = db.query(ContextEmbedding).filter(
                ContextEmbedding.type == embedding_type,
                ContextEmbedding.chat_topic_id == chat_topic.id,
            )
        case "derived_insight":
            query = db.query(ContextEmbedding).filter(
                ContextEmbedding.type == embedding_type,
                ContextEmbedding.derived_insight_id == derived_insight.id,
            )

    existing = query.first() if query is not None else None

    if existing:
        existing.embedding = vector
    else:
        embedding = ContextEmbedding(
            type=embedding_type,
            embedding=vector,
            model_name=os.getenv("EMBEDDING_MODEL_NAME"),
            # 根据来源设置外键
            knowledge_id=knowledge.id if knowledge else None,
            crush_id=crush.id if crush else None,
            event_id=event.id if event else None,
            chat_topic_id=chat_topic.id if chat_topic else None,
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
    top_k: int = 10,
    recall_from: List[
        Literal[
            "knowledge",
            "crush_profile",
            "event",
            "chat_topic",
            "derived_insight",
            "non-knowledge",
            "all",
        ]
    ] = ["all"],
    relation_chain_id: int | None = None,
):
    if not text or not isinstance(text, str) or not text.strip():
        return {"status": -1, "message": "Text is required"}

    if top_k <= 0 or top_k > 100:
        return {"status": -2, "message": "top_k must be between 1 and 100"}

    valid_sources = {
        "knowledge",
        "crush_profile",
        "event",
        "chat_topic",
        "derived_insight",
        "non-knowledge",
        "all",
    }
    if (
        not isinstance(recall_from, list)
        or not recall_from
        or any(item not in valid_sources for item in recall_from)
    ):
        return {"status": -3, "message": "Invalid recall_from"}

    if "non-knowledge" in recall_from:
        recall_from = [
            "crush_profile",
            "event",
            "chat_topic",
            "derived_insight",
        ]
    if "all" in recall_from:
        recall_from = [
            "knowledge",
            "crush_profile",
            "event",
            "chat_topic",
            "derived_insight",
        ]
    if relation_chain_id is None:
        if "knowledge" not in recall_from:
            return {"status": -4, "message": "Relation_chain_id is required"}
        if len(recall_from) > 1:
            recall_from = ["knowledge"]

    try:
        vector = await vectorizeText(text)
    except Exception as e:
        return {"status": -5, "message": f"Embedding generation failed: {str(e)}"}

    if not isinstance(vector, list) or not vector:
        return {"status": -6, "message": "Invalid embedding result"}

    items: list[dict[str, Any]] = []
    message_parts: list[str] = []

    distance = ContextEmbedding.embedding.cosine_distance(vector).label("distance")

    if "knowledge" in recall_from:
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

    if relation_chain_id is not None:
        relation_chain = db.get(RelationChain, relation_chain_id)
        crush_id = relation_chain.crush_id if relation_chain else None

        if "crush_profile" in recall_from:
            if crush_id is None:
                return {"status": -7, "message": "Crush not found in relation chain"}
            else:
                crush_query = (
                    db.query(ContextEmbedding, distance)
                    .filter(
                        ContextEmbedding.type == EmbeddingType.FROM_CRUSH_PROFILE,
                        ContextEmbedding.crush_id == crush_id,
                    )
                    .join(ContextEmbedding.crush)
                    .order_by(distance.asc())
                    .limit(top_k)
                )
                for embedding, dist in crush_query.all():
                    if not embedding.crush:
                        continue
                    items.append(
                        {
                            "source": "crush_profile",
                            "embedding_id": embedding.id,
                            "distance": float(dist),
                            "data": embedding.crush.toJson(),
                        }
                    )

        if "event" in recall_from:
            event_query = (
                db.query(ContextEmbedding, distance)
                .filter(ContextEmbedding.type == EmbeddingType.FROM_EVENT)
                .join(ContextEmbedding.event)
                .filter(
                    Event.is_active.is_(True),
                    Event.relation_chain_id == relation_chain_id,
                )
                .order_by(distance.asc())
                .limit(top_k)
            )
            for embedding, dist in event_query.all():
                if not embedding.event:
                    continue
                items.append(
                    {
                        "source": "event",
                        "embedding_id": embedding.id,
                        "distance": float(dist),
                        "data": embedding.event.toJson(),
                    }
                )

        if "chat_topic" in recall_from:
            chat_topic_query = (
                db.query(ContextEmbedding, distance)
                .filter(ContextEmbedding.type == EmbeddingType.FROM_CHAT_TOPIC)
                .join(ContextEmbedding.chat_topic)
                .filter(
                    ChatTopic.is_active.is_(True),
                    ChatTopic.relation_chain_id == relation_chain_id,
                )
                .order_by(distance.asc())
                .limit(top_k)
            )
            for embedding, dist in chat_topic_query.all():
                if not embedding.chat_topic:
                    continue
                items.append(
                    {
                        "source": "chat_topic",
                        "embedding_id": embedding.id,
                        "distance": float(dist),
                        "data": embedding.chat_topic.toJson(),
                    }
                )

        if "derived_insight" in recall_from:
            derived_insight_query = (
                db.query(ContextEmbedding, distance)
                .filter(ContextEmbedding.type == EmbeddingType.FROM_DERIVED_INSIGHT)
                .join(ContextEmbedding.derived_insight)
                .filter(
                    DerivedInsight.is_active.is_(True),
                    DerivedInsight.relation_chain_id == relation_chain_id,
                )
                .order_by(distance.asc())
                .limit(top_k)
            )
            for embedding, dist in derived_insight_query.all():
                if not embedding.derived_insight:
                    continue
                items.append(
                    {
                        "source": "derived_insight",
                        "embedding_id": embedding.id,
                        "distance": float(dist),
                        "data": embedding.derived_insight.toJson(),
                    }
                )

    items.sort(key=lambda x: x["distance"])
    items = items[:top_k]
    message = "Recall embeddings success"
    if message_parts:
        message = f"{message}; " + "; ".join(message_parts)
    return {"status": 200, "message": message, "items": items}
