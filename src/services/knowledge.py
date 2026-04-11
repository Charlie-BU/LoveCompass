import os
import logging

from src.agents.embedding import vectorizeText
from src.database.index import session
from src.database.models import Knowledge
from src.utils.index import timeDecay


logger = logging.getLogger(__name__)


async def addKnowledgePiece(
    user_id: int,
    content: str,
    weight: float = 0.5,
) -> dict:
    """
    添加知识条目
    """
    if not content or content.strip() == "":
        return {"status": -1, "message": "Content is empty"}
    if weight <= 0 or weight > 1:
        return {"status": -2, "message": "Weight must be between 0 and 1"}

    content = content.strip()
    knowledge = Knowledge(
        user_id=user_id,
        content=content,
        weight=weight,
    )
    # 向量化
    try:
        vector = await vectorizeText(content)
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        return {"status": -3, "message": f"Embedding generation failed"}
    if not isinstance(vector, list) or not vector:
        return {"status": -4, "message": "Invalid embedding result"}

    knowledge.embedding = vector
    knowledge.embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME") or ""

    with session() as db:
        try:
            db.add(knowledge)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Add knowledge failed: {str(e)}")
            return {"status": -5, "message": "Add knowledge failed"}

        return {
            "status": 200,
            "message": "Add knowledge success",
        }


async def recallKnowledgePieces(
    user_id: int,
    query: str,
    top_k: int = 10,
) -> dict:
    """
    召回知识
    """
    if not query or query.strip() == "":
        return {"status": -1, "message": "Query is empty"}
    if top_k <= 0:
        return {"status": -2, "message": "Top_k must be greater than 0"}
    try:
        vector = await vectorizeText(query)
    except Exception as e:
        logger.error(f"Embedding failed: {str(e)}")
        return {"status": -3, "message": f"Embedding failed"}
    if not isinstance(vector, list) or not vector:
        return {"status": -4, "message": "Invalid embedding result"}

    distance = Knowledge.embedding.cosine_distance(vector)

    with session() as db:
        try:
            # 向量距离排序
            candidates: list[tuple[Knowledge, float]] = (
                db.query(Knowledge, distance.label("distance"))
                .filter(Knowledge.user_id == user_id)
                .order_by(distance.asc())
                .limit(int(os.getenv("VECTOR_CANDIDATES")) or 100)
                .all()
            )
        except Exception as e:
            logger.error(f"Recall knowledge failed: {str(e)}")
            return {"status": -5, "message": f"Recall knowledge failed"}

        results = []

        for knowledge, dist in candidates:
            # 语义、权重、时间衰减计算 score
            semantic_score = max(0.0, min(1.0, 1 - float(dist) / 2))
            weight = knowledge.weight
            created_at = knowledge.created_at

            time_decay = timeDecay(created_at) if created_at else 1.0
            raw_score = semantic_score * 0.8 + weight * 0.2
            score = raw_score * time_decay

            results.append(
                {
                    "distance": float(dist),
                    "score": score,
                    "semantic_score": semantic_score,
                    "weight": weight,
                    "time_decay": time_decay,
                    "knowledge": knowledge.toJson(
                        exclude=["embedding", "embedding_model_name"]
                    ),
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:top_k]
        return {
            "status": 200,
            "message": "Recall success",
            "items": results,
        }


def deleteKnowledgePiece(
    user_id: int,
    knowledge_id: int,
) -> dict:
    """
    通过 knowledge_id 软删除知识
    """
    with session() as db:
        try:
            knowledge = (
                db.query(Knowledge)
                .filter(
                    Knowledge.id == knowledge_id,
                    Knowledge.user_id == user_id,
                    Knowledge.is_deleted == False,
                )
                .first()
            )
            if not knowledge:
                return {"status": -1, "message": "Knowledge not found"}
            knowledge.is_deleted = True
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Delete knowledge failed: {str(e)}")
            return {"status": -2, "message": "Delete knowledge failed"}
        return {
            "status": 200,
            "message": "Delete knowledge success",
        }
