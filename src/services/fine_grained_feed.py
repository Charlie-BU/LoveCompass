import logging
import os
from typing import Any, Literal

from sqlalchemy.orm import Session

from src.agents.embedding import vectorizeText
from src.database.enums import FineGrainedFeedConfidence, FineGrainedFeedDimension
from src.database.index import session
from src.database.models import (
    FigureAndRelation,
    FineGrainedFeed,
    FineGrainedFeedConflict,
    OriginalSource,
)


logger = logging.getLogger(__name__)


def _checkFigureAndRelationOwnership(
    db: Session, user_id: int, fr_id: int
) -> FigureAndRelation | None:
    """
    FigureAndRelation 归属校验
    """
    return (
        db.query(FigureAndRelation)
        .filter(
            FigureAndRelation.id == fr_id,
            FigureAndRelation.user_id == user_id,
            FigureAndRelation.is_deleted == False,
        )
        .first()
    )


def _checkOriginalSourceOwnership(
    db,
    user_id: int,
    fr_id: int,
    original_source_id: int,
) -> OriginalSource | None:
    """
    OriginalSource 归属校验
    """
    original_source: OriginalSource | None = (
        db.query(OriginalSource)
        .filter(
            OriginalSource.id == original_source_id,
            OriginalSource.fr_id == fr_id,
            OriginalSource.is_deleted == False,
        )
        .first()
    )
    if original_source is None:
        return None
    if original_source.figure_and_relation.user_id != user_id:
        return None
    return original_source


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
        fr = _checkFigureAndRelationOwnership(
            db=db,
            user_id=user_id,
            fr_id=fr_id,
        )
        if fr is None:
            return {"status": -8, "message": "FigureAndRelation not found"}

        original_source = _checkOriginalSourceOwnership(
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
            vector = await vectorizeText(content)
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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
        if fr is None:
            return {"status": -7, "message": "FigureAndRelation not found"}

        original_source = _checkOriginalSourceOwnership(
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

        fine_grained_feed.original_source_id = new_original_source_id
        fine_grained_feed.content = new_content
        fine_grained_feed.sub_dimension = (
            new_sub_dimension.strip() if isinstance(new_sub_dimension, str) else None
        )
        fine_grained_feed.embedding = vector
        fine_grained_feed.embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME") or ""

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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
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


def addOriginalSource(
    user_id: int,
    fr_id: int,
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
    if not isinstance(confidence, FineGrainedFeedConfidence):
        return {"status": -3, "message": "Invalid confidence"}
    if (
        not isinstance(included_dimensions, list)
        or not included_dimensions
        or not all(
            isinstance(item, FineGrainedFeedDimension) for item in included_dimensions
        )
    ):
        return {"status": -4, "message": "Invalid included_dimensions"}
    if not content or content.strip() == "":
        return {"status": -5, "message": "content cannot be empty"}
    if approx_date is not None and not isinstance(approx_date, str):
        return {"status": -6, "message": "Invalid approx_date"}

    with session() as db:
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
        if fr is None:
            return {"status": -7, "message": "FigureAndRelation not found"}

        original_source = OriginalSource(
            fr_id=fr_id,
            approx_date=approx_date if approx_date is not None else None,
            confidence=confidence,
            included_dimensions=included_dimensions,
            content=content.strip(),
        )
        try:
            db.add(original_source)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Add OriginalSource failed: {str(e)}")
            return {"status": -8, "message": "Add OriginalSource failed"}

        return {"status": 200, "message": "Add OriginalSource success"}


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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
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
    description: str,
    resolved: bool = False,
    resolution: str | None = None,
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
    if not description or description.strip() == "":
        return {"status": -5, "message": "description cannot be empty"}
    if not isinstance(resolved, bool):
        return {"status": -6, "message": "Invalid resolved"}
    if resolution is not None and not isinstance(resolution, str):
        return {"status": -7, "message": "Invalid resolution"}

    with session() as db:
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
        if fr is None:
            return {"status": -8, "message": "FigureAndRelation not found"}
        if not _checkFineGrainedFeedIds(db, fr_id, feed_ids):
            return {"status": -9, "message": "Invalid feed_ids"}

        fine_grained_feed_conflict = FineGrainedFeedConflict(
            fr_id=fr_id,
            dimension=dimension,
            feed_ids=feed_ids,
            description=description.strip(),
            resolved=resolved,
            resolution=resolution if resolution is not None else None,
        )

        try:
            db.add(fine_grained_feed_conflict)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Add FineGrainedFeedConflict failed: {str(e)}")
            return {"status": -10, "message": "Add FineGrainedFeedConflict failed"}

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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
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

    with session() as db:
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
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
            if fine_grained_feed_conflict.resolved:
                return {
                    "status": -6,
                    "message": "FineGrainedFeedConflict already resolved",
                }

            fine_grained_feed_conflict.resolved = True
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Resolve FineGrainedFeedConflict failed: {str(e)}")
            return {"status": -7, "message": "Resolve FineGrainedFeedConflict failed"}

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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
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
        fr = _checkFigureAndRelationOwnership(db, user_id, fr_id)
        if fr is None:
            return {"status": -3, "message": "FigureAndRelation not found"}

        query = db.query(FineGrainedFeedConflict).filter(
            FineGrainedFeedConflict.fr_id == fr_id
        )

        match scope:
            case "all":
                pass
            case "unresolved":
                query = query.filter(FineGrainedFeedConflict.resolved == False)
            case "resolved":
                query = query.filter(FineGrainedFeedConflict.resolved == True)
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
                        "resolved",
                        "created_at",
                    ]
                )
                for item in fine_grained_feed_conflicts
            ],
        }
