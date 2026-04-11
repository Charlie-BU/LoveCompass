import logging
from typing import Any

from src.database.enums import FigureRole, Gender, MBTI
from src.database.index import session
from src.database.models import FigureAndRelation


logger = logging.getLogger(__name__)


def _frUpdateFieldCheck(fr_body: dict[str, Any]) -> dict[str, Any]:
    """
    校验 FigureAndRelation 更新字段是否合法
    """
    allowed_fields = {
        "figure_name",
        "figure_gender",
        "figure_role",
        "figure_mbti",
        "figure_birthday",
        "figure_occupation",
        "figure_education",
        "figure_residence",
        "figure_hometown",
        "figure_likes",
        "figure_dislikes",
        "figure_appearance",
        "words_figure2user",
        "words_user2figure",
        "exact_relation",
        "core_personality",
        "core_interaction_style",
        "core_procedural_info",
        "core_memory",
    }
    non_nullable_fields = {
        "figure_name",
        "figure_gender",
        "figure_role",
        "figure_likes",
        "figure_dislikes",
        "figure_appearance",
        "words_figure2user",
        "words_user2figure",
        "exact_relation",
        "core_personality",
        "core_interaction_style",
        "core_procedural_info",
        "core_memory",
    }
    list_fields = {
        "figure_likes",
        "figure_dislikes",
        "figure_appearance",
        "words_figure2user",
        "words_user2figure",
    }
    string_fields = {
        "figure_name",
        "figure_birthday",
        "figure_occupation",
        "figure_education",
        "figure_residence",
        "figure_hometown",
        "exact_relation",
        "core_personality",
        "core_interaction_style",
        "core_procedural_info",
        "core_memory",
    }

    invalid_fields = [field for field in fr_body if field not in allowed_fields]
    if invalid_fields:
        raise ValueError(f"Invalid fields: {', '.join(sorted(invalid_fields))}")

    updates: dict[str, Any] = {}
    for field, value in fr_body.items():
        # 格式 / 类型校验
        # 非 nullable 字段
        if field in non_nullable_fields:
            if (
                not value
                or (isinstance(value, str) and value.strip() == "")
                or (isinstance(value, list) and len(value) == 0)
                or (isinstance(value, dict) and len(value) == 0)
            ):
                raise ValueError(f"{field} cannot be empty")
        # 枚举类型
        elif field == "figure_gender":
            if not isinstance(value, Gender):
                raise ValueError("Invalid figure gender")
        if field == "figure_role":
            if not isinstance(value, FigureRole):
                raise ValueError("Invalid figure role")
        elif field == "figure_mbti":
            if value is not None and not isinstance(value, MBTI):  # 允许 value 为 None
                raise ValueError("Invalid figure MBTI")
        # 数组类型
        elif field in list_fields:
            if not isinstance(value, list):
                raise ValueError(f"{field} must be a list")
        # 字符串类型
        elif field in string_fields:
            if not isinstance(value, str):
                raise ValueError(f"{field} must be a string")

        updates[field] = value
    return updates


def addFigureAndRelation(
    user_id: int,
    figure_name: str,
    figure_gender: Gender,
    figure_role: FigureRole,
    figure_mbti: MBTI | None = None,
    figure_birthday: str | None = None,
    figure_occupation: str | None = None,
    figure_education: str | None = None,
    figure_residence: str | None = None,
    figure_hometown: str | None = None,
    exact_relation: str | None = "",
) -> dict:
    """
    添加 FigureAndRelation
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not figure_name or figure_name.strip() == "":
        return {"status": -2, "message": "figure_name cannot be empty"}

    figure_and_relation = FigureAndRelation(
        user_id=user_id,
        figure_name=figure_name.strip(),
        figure_gender=figure_gender,
        figure_role=figure_role,
        figure_mbti=figure_mbti if figure_mbti is not None else None,
        figure_birthday=figure_birthday if figure_birthday is not None else None,
        figure_occupation=figure_occupation if figure_occupation is not None else None,
        figure_education=figure_education if figure_education is not None else None,
        figure_residence=figure_residence if figure_residence is not None else None,
        figure_hometown=figure_hometown if figure_hometown is not None else None,
        exact_relation=exact_relation if exact_relation is not None else "",
    )

    with session() as db:
        try:
            db.add(figure_and_relation)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Add FigureAndRelation failed: {str(e)}")
            return {"status": -3, "message": "Add FigureAndRelation failed"}

        return {
            "status": 200,
            "message": "Add FigureAndRelation success",
        }


def deleteFigureAndRelation(
    user_id: int,
    fr_id: int,
) -> dict:
    """
    通过 fr_id 软删除 FigureAndRelation
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}

    with session() as db:
        try:
            figure_and_relation = (
                db.query(FigureAndRelation)
                .filter(
                    FigureAndRelation.id == fr_id,
                    FigureAndRelation.user_id == user_id,
                    FigureAndRelation.is_deleted == False,
                )
                .first()
            )
            if figure_and_relation is None:
                return {"status": -3, "message": "FigureAndRelation not found"}
            figure_and_relation.is_deleted = True
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Delete FigureAndRelation failed: {str(e)}")
            return {"status": -4, "message": "Delete FigureAndRelation failed"}

        return {
            "status": 200,
            "message": "Delete FigureAndRelation success",
        }


def updateFigureAndRelation(
    user_id: int,
    fr_id: int,
    fr_body: dict[str, Any],
) -> dict:
    """
    通过 fr_id 更新 FigureAndRelation
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(fr_body, dict):
        return {"status": -3, "message": "fr_body must be a dict"}
    if not fr_body or fr_body == {}:
        return {"status": -4, "message": "fr_body is empty"}

    try:
        updates = _frUpdateFieldCheck(fr_body)
    except ValueError as e:
        return {"status": -5, "message": str(e)}

    with session() as db:
        try:
            figure_and_relation = (
                db.query(FigureAndRelation)
                .filter(
                    FigureAndRelation.id == fr_id,
                    FigureAndRelation.user_id == user_id,
                    FigureAndRelation.is_deleted == False,
                )
                .first()
            )
            if figure_and_relation is None:
                return {"status": -6, "message": "FigureAndRelation not found"}

            for field, value in updates.items():
                setattr(figure_and_relation, field, value)

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Update FigureAndRelation failed: {str(e)}")
            return {"status": -7, "message": "Update FigureAndRelation failed"}

        return {
            "status": 200,
            "message": "Update FigureAndRelation success",
        }


def getFigureAndRelation(
    user_id: int,
    fr_id: int,
) -> dict:
    """
    通过 fr_id 获取 FigureAndRelation
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}

    with session() as db:
        figure_and_relation = (
            db.query(FigureAndRelation)
            .filter(
                FigureAndRelation.id == fr_id,
                FigureAndRelation.user_id == user_id,
                FigureAndRelation.is_deleted == False,
            )
            .first()
        )
        if figure_and_relation is None:
            return {"status": -3, "message": "FigureAndRelation not found"}
        return {
            "status": 200,
            "message": "Get FigureAndRelation success",
            "figure_and_relation": figure_and_relation.toJson(),
        }


def getAllFigureAndRelations(
    user_id: int,
) -> dict:
    """
    获取用户所有 FigureAndRelation
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}

    with session() as db:
        figure_and_relations = (
            db.query(FigureAndRelation)
            .filter(
                FigureAndRelation.user_id == user_id,
                FigureAndRelation.is_deleted == False,
            )
            .order_by(FigureAndRelation.updated_at.desc())
            .all()
        )
        return {
            "status": 200,
            "message": "Get all FigureAndRelation success",
            "figure_and_relations": [
                fr.toJson(
                    include=[
                        "id",
                        "user_id",
                        "figure_role",
                        "figure_name",
                        "figure_gender",
                        "is_deleted",
                        "created_at",
                        "updated_at",
                    ]
                )
                for fr in figure_and_relations
            ],
        }
