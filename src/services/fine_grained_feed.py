import logging
import os
from typing import List, Literal, TypedDict

from src.agents.embedding import vectorizeText
from src.database.enums import (
    ConflictStatus,
    FineGrainedFeedConfidence,
    FineGrainedFeedDimension,
    OriginalSourceType,
)
from src.database.index import session
from src.database.models import (
    FROverallUpdateLog,
    FineGrainedFeed,
    FineGrainedFeedConflict,
    OriginalSource,
)
from src.utils.index import (
    serialize2String,
    timeDecay,
    checkFigureAndRelationOwnershipInDB,
    checkOriginalSourceOwnershipInDB,
)


logger = logging.getLogger(__name__)


def _checkFineGrainedFeedIds(
    db,
    fr_id: int,
    feed_ids: list[int],
) -> bool:
    if not feed_ids:
        return False
    if not all(isinstance(feed_id, int) for feed_id in feed_ids):
        return False
    count = (
        db.query(FineGrainedFeed)
        .filter(
            FineGrainedFeed.id.in_(feed_ids),
            FineGrainedFeed.fr_id == fr_id,
            FineGrainedFeed.is_deleted == False,
        )
        .count()
    )
    return count == len(set(feed_ids))


async def addFineGrainedFeed(
    user_id: int,
    fr_id: int,
    original_source_id: int,
    dimension: FineGrainedFeedDimension,
    confidence: FineGrainedFeedConfidence,
    content: str,
    sub_dimension: str | None = None,
) -> dict:
    """
    添加细粒度信息
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(original_source_id, int):
        return {"status": -3, "message": "Invalid original_source_id"}
    if not isinstance(dimension, FineGrainedFeedDimension):
        return {"status": -4, "message": "Invalid dimension"}
    if not isinstance(confidence, FineGrainedFeedConfidence):
        return {"status": -5, "message": "Invalid confidence"}
    if not content or content.strip() == "":
        return {"status": -6, "message": "content cannot be empty"}
    if sub_dimension is not None and not isinstance(sub_dimension, str):
        return {"status": -7, "message": "Invalid sub_dimension"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(
            db=db,
            user_id=user_id,
            fr_id=fr_id,
        )
        if fr is None:
            return {"status": -8, "message": "FigureAndRelation not found"}

        original_source = checkOriginalSourceOwnershipInDB(
            db=db,
            user_id=user_id,
            fr_id=fr_id,
            original_source_id=original_source_id,
        )
        if original_source is None:
            return {"status": -9, "message": "OriginalSource not found"}

        content = content.strip()
        fine_grained_feed = FineGrainedFeed(
            fr_id=fr_id,
            original_source_id=original_source_id,
            dimension=dimension,
            sub_dimension=sub_dimension if sub_dimension is not None else None,
            confidence=confidence,
            content=content,
        )

        # 向量化
        try:
            vector = await vectorizeText(
                f"{sub_dimension}{"\n" if sub_dimension else ""}{content}"
            )
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            return {"status": -10, "message": f"Embedding generation failed"}
        if not isinstance(vector, list) or not vector:
            return {"status": -11, "message": "Invalid embedding result"}

        fine_grained_feed.embedding = vector
        fine_grained_feed.embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME") or ""

        try:
            db.add(fine_grained_feed)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Add FineGrainedFeed failed: {str(e)}")
            return {"status": -12, "message": "Add FineGrainedFeed failed"}

        return {"status": 200, "message": "Add FineGrainedFeed success"}


def deleteFineGrainedFeed(
    user_id: int,
    fr_id: int,
    fine_grained_feed_id: int,
) -> dict:
    """
    通过 fine_grained_feed_id 软删除细粒度信息
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(fine_grained_feed_id, int):
        return {"status": -3, "message": "Invalid fine_grained_feed_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}
        try:
            fine_grained_feed = (
                db.query(FineGrainedFeed)
                .filter(
                    FineGrainedFeed.id == fine_grained_feed_id,
                    FineGrainedFeed.fr_id == fr_id,
                    FineGrainedFeed.is_deleted == False,
                )
                .first()
            )
            if fine_grained_feed is None:
                return {"status": -5, "message": "FineGrainedFeed not found"}
            fine_grained_feed.is_deleted = True
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Delete FineGrainedFeed failed: {str(e)}")
            return {"status": -6, "message": "Delete FineGrainedFeed failed"}
        return {"status": 200, "message": "Delete FineGrainedFeed success"}


async def updateFineGrainedFeed(
    user_id: int,
    fr_id: int,
    fine_grained_feed_id: int,
    new_original_source_id: int,
    new_content: str,
    new_sub_dimension: str | None = None,
) -> dict:
    """
    通过 fine_grained_feed_id 更新细粒度信息（仅修改关联original_source、文本内容、子维度）
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(fine_grained_feed_id, int):
        return {"status": -3, "message": "Invalid fine_grained_feed_id"}
    if not isinstance(new_original_source_id, int):
        return {"status": -4, "message": "Invalid new_original_source_id"}
    if not isinstance(new_content, str) or new_content.strip() == "":
        return {"status": -5, "message": "new_content cannot be empty"}
    if new_sub_dimension is not None and not isinstance(new_sub_dimension, str):
        return {"status": -6, "message": "Invalid new_sub_dimension"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -7, "message": "FigureAndRelation not found"}

        original_source = checkOriginalSourceOwnershipInDB(
            db=db,
            user_id=user_id,
            fr_id=fr_id,
            original_source_id=new_original_source_id,
        )
        if original_source is None:
            return {"status": -8, "message": "OriginalSource not found"}

        fine_grained_feed = (
            db.query(FineGrainedFeed)
            .filter(
                FineGrainedFeed.id == fine_grained_feed_id,
                FineGrainedFeed.fr_id == fr_id,
                FineGrainedFeed.is_deleted == False,
            )
            .first()
        )
        if fine_grained_feed is None:
            return {"status": -9, "message": "FineGrainedFeed not found"}

        new_content = new_content.strip()
        try:
            vector = await vectorizeText(new_content)
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            return {"status": -10, "message": f"Embedding generation failed"}
        if not isinstance(vector, list) or not vector:
            return {"status": -11, "message": "Invalid embedding result"}

        old_content = fine_grained_feed.content
        fine_grained_feed.original_source_id = new_original_source_id
        fine_grained_feed.content = new_content
        fine_grained_feed.sub_dimension = (
            new_sub_dimension.strip() if isinstance(new_sub_dimension, str) else None
        )
        fine_grained_feed.embedding = vector
        fine_grained_feed.embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME") or ""
        db.add(
            FROverallUpdateLog(
                fr_id=fr_id,
                original_source_id=new_original_source_id,
                update_field_or_sub_dimension=fine_grained_feed.sub_dimension or "",
                update_dimension=fine_grained_feed.dimension,
                old_value=serialize2String(old_content),
                new_value=serialize2String(fine_grained_feed.content),
            )
        )

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Update FineGrainedFeed failed: {str(e)}")
            return {"status": -12, "message": "Update FineGrainedFeed failed"}

        return {"status": 200, "message": "Update FineGrainedFeed success"}


def getFineGrainedFeed(
    user_id: int,
    fr_id: int,
    fine_grained_feed_id: int,
) -> dict:
    """
    通过 fine_grained_feed_id 获取细粒度信息详情
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(fine_grained_feed_id, int):
        return {"status": -3, "message": "Invalid fine_grained_feed_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}

        fine_grained_feed = (
            db.query(FineGrainedFeed)
            .filter(
                FineGrainedFeed.id == fine_grained_feed_id,
                FineGrainedFeed.fr_id == fr_id,
                FineGrainedFeed.is_deleted == False,
            )
            .first()
        )
        if fine_grained_feed is None:
            return {"status": -5, "message": "FineGrainedFeed not found"}
        return {
            "status": 200,
            "message": "Get FineGrainedFeed success",
            "fine_grained_feed": fine_grained_feed.toJson(
                exclude=["embedding", "embedding_model_name"]
            ),
        }


def getAllFineGrainedFeed(
    user_id: int,
    fr_id: int,
) -> dict:
    """
    获取当前 fr 所有细粒度信息（不包含详情）
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -3, "message": "FigureAndRelation not found"}

        fine_grained_feeds = (
            db.query(FineGrainedFeed)
            .filter(
                FineGrainedFeed.fr_id == fr_id,
                FineGrainedFeed.is_deleted == False,
            )
            .order_by(FineGrainedFeed.updated_at.desc())
            .all()
        )
        return {
            "status": 200,
            "message": "Get all FineGrainedFeed success",
            "fine_grained_feeds": [
                item.toJson(
                    include=[
                        "id",
                        "fr_id",
                        "original_source_id",
                        "dimension",
                        "is_deleted",
                        "created_at",
                        "updated_at",
                    ]
                )
                for item in fine_grained_feeds
            ],
        }


class _recallScopeAndTopK(TypedDict):
    scope: FineGrainedFeedDimension | Literal["all"]
    top_k: int


async def recallFineGrainedFeeds(
    user_id: int,
    fr_id: int,
    scope: List[_recallScopeAndTopK],
    query: str | None = None,
) -> dict:
    """
    召回细粒度信息
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if query is not None and not isinstance(query, str):
        return {"status": -3, "message": "Invalid query"}
    if not isinstance(scope, list) or not scope:
        return {"status": -4, "message": "Scope config is invalid"}

    # scope 配置归一为 (FineGrainedFeedDimension | Literal["all"], int)
    normalized_scope_cfg: list[
        tuple[FineGrainedFeedDimension | Literal["all"], int]
    ] = []
    seen_scope_items: set[FineGrainedFeedDimension | Literal["all"]] = set()
    for item in scope:
        if not isinstance(item, dict):
            return {"status": -9, "message": "Invalid scope item"}
        item_scope = item.get("scope")
        item_top_k = item.get("top_k")
        if item_scope != "all" and not isinstance(item_scope, FineGrainedFeedDimension):
            return {"status": -9, "message": "Invalid scope item"}
        if not isinstance(item_top_k, int) or item_top_k <= 0:
            return {"status": -4, "message": "Top_k must be greater than 0"}
        if item_scope in seen_scope_items:
            return {"status": -10, "message": "Duplicate scope is not allowed"}
        seen_scope_items.add(item_scope)
        normalized_scope_cfg.append((item_scope, item_top_k))

    has_query = query is not None and query.strip() != ""
    if has_query:
        query = query.strip()
    distance = None

    if has_query:
        # query 不为空：走向量召回逻辑
        try:
            vector = await vectorizeText(query)
        except Exception as e:
            logger.error(f"Embedding failed: {str(e)}")
            return {"status": -5, "message": "Embedding failed"}
        if not isinstance(vector, list) or not vector:
            return {"status": -6, "message": "Invalid embedding result"}
        distance = FineGrainedFeed.embedding.cosine_distance(vector)

    confidence_weight_map = {
        FineGrainedFeedConfidence.VERBATIM: 1.0,
        FineGrainedFeedConfidence.ARTIFACT: 0.85,
        FineGrainedFeedConfidence.IMPRESSION: 0.7,
    }

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -7, "message": "FigureAndRelation not found"}
        try:
            vector_candidates_limit = int(os.getenv("VECTOR_CANDIDATES") or 100)
        except Exception as e:
            logger.error(f"Recall FineGrainedFeed failed: {str(e)}")
            return {"status": -8, "message": "Recall FineGrainedFeed failed"}

        results = {}
        # 分别按 scope 召回
        for scope_item, scope_top_k in normalized_scope_cfg:
            if has_query:
                # query 不为空：走向量召回逻辑
                db_query = db.query(FineGrainedFeed, distance.label("distance")).filter(
                    FineGrainedFeed.fr_id == fr_id,
                    FineGrainedFeed.is_deleted == False,
                )
            else:
                # query 为空：先获取全部 feeds
                db_query = db.query(FineGrainedFeed).filter(
                    FineGrainedFeed.fr_id == fr_id,
                    FineGrainedFeed.is_deleted == False,
                )
            if scope_item != "all":
                # 按 scope 筛选
                db_query = db_query.filter(FineGrainedFeed.dimension == scope_item)

            if has_query:
                candidates = (
                    db_query.order_by(distance.asc())
                    .limit(max(vector_candidates_limit, scope_top_k))
                    .all()
                )
            else:
                candidates = db_query.all()

            per_scope_results = []
            # 对每个召回项计算 score，重排
            for candidate in candidates:
                if has_query:
                    fine_grained_feed, dist = candidate
                    semantic_score = max(0.0, min(1.0, 1 - float(dist) / 2))
                else:
                    fine_grained_feed = candidate
                    dist = None
                    semantic_score = None
                confidence_weight = confidence_weight_map.get(
                    fine_grained_feed.confidence, 0.7
                )
                created_at = fine_grained_feed.created_at

                decay = timeDecay(created_at) if created_at else 1.0
                if has_query:
                    # query 不为空：语义分和置信度共同计算分数
                    raw_score = semantic_score * 0.8 + confidence_weight * 0.2
                else:
                    # query 为空：仅用置信度计算分数
                    raw_score = confidence_weight
                score = raw_score * decay

                per_scope_results.append(
                    {
                        "distance": float(dist) if dist is not None else None,
                        "score": score,
                        "semantic_score": semantic_score,
                        "confidence_weight": confidence_weight,
                        "time_decay": decay,
                        "fine_grained_feed": fine_grained_feed.toJson(
                            exclude=["embedding", "embedding_model_name"]
                        ),
                    }
                )

            per_scope_results.sort(key=lambda x: x["score"], reverse=True)
            if scope_item != "all":
                results[scope_item.value] = per_scope_results[:scope_top_k]
            else:
                # scope 为 all，按维度分组
                grouped_by_dimension: dict[str, list[dict]] = {}
                for item in per_scope_results[:scope_top_k]:
                    fine_grained_feed = item.get("fine_grained_feed") or {}
                    dimension = fine_grained_feed.get("dimension")
                    if not isinstance(dimension, str) or dimension == "":
                        continue
                    grouped_by_dimension.setdefault(dimension, []).append(item)
                for dimension, items in grouped_by_dimension.items():
                    results.setdefault(dimension, []).extend(items)

        return {
            "status": 200,
            "message": "Recall success",
            "items": results,
        }


def addOriginalSource(
    user_id: int,
    fr_id: int,
    type: OriginalSourceType,
    confidence: FineGrainedFeedConfidence,
    included_dimensions: list[FineGrainedFeedDimension],
    content: str,
    approx_date: str | None = None,
) -> dict:
    """
    添加原始信息来源
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(type, OriginalSourceType):
        return {"status": -3, "message": "Invalid type"}
    if not isinstance(confidence, FineGrainedFeedConfidence):
        return {"status": -4, "message": "Invalid confidence"}
    if (
        not isinstance(included_dimensions, list)
        or not included_dimensions
        or not all(
            isinstance(item, FineGrainedFeedDimension) for item in included_dimensions
        )
    ):
        return {"status": -5, "message": "Invalid included_dimensions"}
    if not content or content.strip() == "":
        return {"status": -6, "message": "content cannot be empty"}
    if approx_date is not None and not isinstance(approx_date, str):
        return {"status": -7, "message": "Invalid approx_date"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -8, "message": "FigureAndRelation not found"}

        original_source = OriginalSource(
            fr_id=fr_id,
            type=type,
            approx_date=approx_date if approx_date is not None else None,
            confidence=confidence,
            included_dimensions=included_dimensions,
            content=content.strip(),
        )
        try:
            db.add(original_source)
            db.commit()
            db.refresh(original_source)
        except Exception as e:
            db.rollback()
            logger.error(f"Add OriginalSource failed: {str(e)}")
            return {"status": -9, "message": "Add OriginalSource failed"}

        return {
            "status": 200,
            "message": "Add OriginalSource success",
            "original_source_id": original_source.id,
        }


def deleteOriginalSource(
    user_id: int,
    fr_id: int,
    original_source_id: int,
) -> dict:
    """
    通过 original_source_id 软删除原始信息来源
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(original_source_id, int):
        return {"status": -3, "message": "Invalid original_source_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}

        try:
            original_source = (
                db.query(OriginalSource)
                .filter(
                    OriginalSource.id == original_source_id,
                    OriginalSource.fr_id == fr_id,
                    OriginalSource.is_deleted == False,
                )
                .first()
            )
            if original_source is None:
                return {"status": -5, "message": "OriginalSource not found"}
            original_source.is_deleted = True
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Delete OriginalSource failed: {str(e)}")
            return {"status": -6, "message": "Delete OriginalSource failed"}

        return {"status": 200, "message": "Delete OriginalSource success"}


def getOriginalSource(
    user_id: int,
    fr_id: int,
    original_source_id: int,
) -> dict:
    """
    通过 original_source_id 获取原始信息来源详情
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(original_source_id, int):
        return {"status": -3, "message": "Invalid original_source_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}

        original_source = (
            db.query(OriginalSource)
            .filter(
                OriginalSource.id == original_source_id,
                OriginalSource.fr_id == fr_id,
                OriginalSource.is_deleted == False,
            )
            .first()
        )
        if original_source is None:
            return {"status": -5, "message": "OriginalSource not found"}
        return {
            "status": 200,
            "message": "Get OriginalSource success",
            "original_source": original_source.toJson(),
        }


def getAllOriginalSource(
    user_id: int,
    fr_id: int,
) -> dict:
    """
    获取当前 fr 所有原始信息来源（不包含详情）
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -3, "message": "FigureAndRelation not found"}

        original_sources = (
            db.query(OriginalSource)
            .filter(
                OriginalSource.fr_id == fr_id,
                OriginalSource.is_deleted == False,
            )
            .order_by(OriginalSource.updated_at.desc())
            .all()
        )
        return {
            "status": 200,
            "message": "Get all OriginalSource success",
            "original_sources": [
                item.toJson(
                    include=[
                        "id",
                        "fr_id",
                        "approx_date",
                        "confidence",
                        "is_deleted",
                        "created_at",
                        "updated_at",
                    ]
                )
                for item in original_sources
            ],
        }


def addFineGrainedFeedConflict(
    user_id: int,
    fr_id: int,
    dimension: FineGrainedFeedDimension,
    feed_ids: list[int],
    old_value: str,
    new_value: str,
    conflict_detail: str,
    status: ConflictStatus = ConflictStatus.PENDING,
) -> dict:
    """
    添加细粒度信息冲突
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(dimension, FineGrainedFeedDimension):
        return {"status": -3, "message": "Invalid dimension"}
    if not isinstance(feed_ids, list) or not all(
        isinstance(item, int) for item in feed_ids
    ):
        return {"status": -4, "message": "Invalid feed_ids"}
    if not isinstance(old_value, str) or old_value.strip() == "":
        return {"status": -5, "message": "old_value cannot be empty"}
    if not isinstance(new_value, str) or new_value.strip() == "":
        return {"status": -6, "message": "new_value cannot be empty"}
    if not conflict_detail or conflict_detail.strip() == "":
        return {"status": -7, "message": "conflict_detail cannot be empty"}
    if not isinstance(status, ConflictStatus):
        return {"status": -10, "message": "Invalid status"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -8, "message": "FigureAndRelation not found"}
        if not _checkFineGrainedFeedIds(db, fr_id, feed_ids):
            return {"status": -9, "message": "Invalid feed_ids"}

        fine_grained_feed_conflict = FineGrainedFeedConflict(
            fr_id=fr_id,
            dimension=dimension,
            feed_ids=feed_ids,
            old_value=old_value.strip(),
            new_value=new_value.strip(),
            conflict_detail=conflict_detail.strip(),
            status=status,
        )

        try:
            db.add(fine_grained_feed_conflict)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Add FineGrainedFeedConflict failed: {str(e)}")
            return {"status": -11, "message": "Add FineGrainedFeedConflict failed"}

        return {"status": 200, "message": "Add FineGrainedFeedConflict success"}


def hardDeleteFineGrainedFeedConflict(
    user_id: int,
    fr_id: int,
    fine_grained_feed_conflict_id: int,
) -> dict:
    """
    通过 fine_grained_feed_conflict_id 硬删除细粒度信息冲突
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(fine_grained_feed_conflict_id, int):
        return {"status": -3, "message": "Invalid fine_grained_feed_conflict_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}

        try:
            fine_grained_feed_conflict = (
                db.query(FineGrainedFeedConflict)
                .filter(
                    FineGrainedFeedConflict.id == fine_grained_feed_conflict_id,
                    FineGrainedFeedConflict.fr_id == fr_id,
                )
                .first()
            )
            if fine_grained_feed_conflict is None:
                return {"status": -5, "message": "FineGrainedFeedConflict not found"}
            db.delete(fine_grained_feed_conflict)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Delete FineGrainedFeedConflict failed: {str(e)}")
            return {"status": -6, "message": "Delete FineGrainedFeedConflict failed"}

        return {"status": 200, "message": "Delete FineGrainedFeedConflict success"}


def resolveFineGrainedFeedConflict(
    user_id: int,
    fr_id: int,
    fine_grained_feed_conflict_id: int,
    status: ConflictStatus,
) -> dict:
    """
    解决细粒度信息冲突
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(fine_grained_feed_conflict_id, int):
        return {"status": -3, "message": "Invalid fine_grained_feed_conflict_id"}
    if not isinstance(status, ConflictStatus):
        return {"status": -4, "message": "Invalid status"}
    if status == ConflictStatus.PENDING:
        return {"status": -5, "message": "status cannot be pending when resolving"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -6, "message": "FigureAndRelation not found"}

        try:
            fine_grained_feed_conflict = (
                db.query(FineGrainedFeedConflict)
                .filter(
                    FineGrainedFeedConflict.id == fine_grained_feed_conflict_id,
                    FineGrainedFeedConflict.fr_id == fr_id,
                )
                .first()
            )
            if fine_grained_feed_conflict is None:
                return {"status": -7, "message": "FineGrainedFeedConflict not found"}
            if fine_grained_feed_conflict.status != ConflictStatus.PENDING:
                return {
                    "status": -8,
                    "message": "FineGrainedFeedConflict already resolved",
                }

            fine_grained_feed_conflict.status = status
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Resolve FineGrainedFeedConflict failed: {str(e)}")
            return {"status": -9, "message": "Resolve FineGrainedFeedConflict failed"}

        return {"status": 200, "message": "Resolve FineGrainedFeedConflict success"}


def getFineGrainedFeedConflict(
    user_id: int,
    fr_id: int,
    fine_grained_feed_conflict_id: int,
) -> dict:
    """
    通过 fine_grained_feed_conflict_id 获取细粒度信息冲突详情
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(fine_grained_feed_conflict_id, int):
        return {"status": -3, "message": "Invalid fine_grained_feed_conflict_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}

        fine_grained_feed_conflict = (
            db.query(FineGrainedFeedConflict)
            .filter(
                FineGrainedFeedConflict.id == fine_grained_feed_conflict_id,
                FineGrainedFeedConflict.fr_id == fr_id,
            )
            .first()
        )
        if fine_grained_feed_conflict is None:
            return {"status": -5, "message": "FineGrainedFeedConflict not found"}
        return {
            "status": 200,
            "message": "Get FineGrainedFeedConflict success",
            "fine_grained_feed_conflict": fine_grained_feed_conflict.toJson(),
        }


def getAllFineGrainedFeedConflict(
    user_id: int,
    fr_id: int,
    scope: Literal["all", "unresolved", "resolved"] = "unresolved",
) -> dict:
    """
    获取当前 fr 所有细粒度信息冲突（不包含详情）
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnershipInDB(db, user_id, fr_id)
        if fr is None:
            return {"status": -3, "message": "FigureAndRelation not found"}

        query = db.query(FineGrainedFeedConflict).filter(
            FineGrainedFeedConflict.fr_id == fr_id
        )

        match scope:
            case "all":
                pass
            case "unresolved":
                query = query.filter(
                    FineGrainedFeedConflict.status == ConflictStatus.PENDING
                )
            case "resolved":
                query = query.filter(
                    FineGrainedFeedConflict.status != ConflictStatus.PENDING
                )
            case _:
                return {"status": -4, "message": "Invalid scope"}

        fine_grained_feed_conflicts = query.order_by(
            FineGrainedFeedConflict.created_at.desc()
        ).all()
        return {
            "status": 200,
            "message": "Get all FineGrainedFeedConflict success",
            "fine_grained_feed_conflicts": [
                item.toJson(
                    include=[
                        "id",
                        "fr_id",
                        "dimension",
                        "feed_ids",
                        "old_value",
                        "new_value",
                        "status",
                        "created_at",
                    ]
                )
                for item in fine_grained_feed_conflicts
            ],
        }
