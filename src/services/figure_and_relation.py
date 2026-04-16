import logging
from typing import Any

from src.database.enums import FigureRole, FineGrainedFeedDimension, Gender, MBTI
from src.database.index import session
from src.database.models import (
    FRBuildingGraphReport,
    FROverallUpdateLog,
    FigureAndRelation,
)
from src.services.fine_grained_feed import recallFineGrainedFeeds
from src.utils.index import checkFigureAndRelationOwnership, serialize2String


logger = logging.getLogger(__name__)

fr_allowed_fields = {
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
fr_non_nullable_fields = {
    "figure_name",
    "figure_gender",
    "figure_role",
    "figure_likes",
    "figure_dislikes",
    "words_figure2user",
    "words_user2figure",
    "exact_relation",
    "core_personality",
    "core_interaction_style",
    "core_procedural_info",
    "core_memory",
}
fr_list_fields = {
    "figure_likes",
    "figure_dislikes",
    "words_figure2user",
    "words_user2figure",
}


def fr_string_fields(detailed: bool = False):
    fields = {
        "figure_birthday",
        "figure_occupation",
        "figure_education",
        "figure_residence",
        "figure_hometown",
        "figure_appearance",
        "exact_relation",
    }
    if not detailed:
        return fields
    fields.add("figure_name")
    fields.add("core_personality")
    fields.add("core_interaction_style")
    fields.add("core_procedural_info")
    fields.add("core_memory")
    return fields


def _frUpdateFieldCheck(fr_body: dict[str, Any]) -> dict[str, Any]:
    """
    校验 FigureAndRelation 更新字段是否合法
    """

    invalid_fields = [field for field in fr_body if field not in fr_allowed_fields]
    if invalid_fields:
        raise ValueError(f"Invalid fields: {', '.join(sorted(invalid_fields))}")

    updates: dict[str, Any] = {}
    for field, value in fr_body.items():
        # 格式 / 类型校验
        # 非 nullable 字段
        if field in fr_non_nullable_fields:
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
        elif field in fr_list_fields:
            if not isinstance(value, list):
                raise ValueError(f"{field} must be a list")
        # 字符串类型
        elif field in fr_string_fields(detailed=True):
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

            fr_logs = []
            for field, value in updates.items():
                old_value = getattr(figure_and_relation, field)
                setattr(figure_and_relation, field, value)
                fr_logs.append(
                    FROverallUpdateLog(
                        fr_id=fr_id,
                        update_field_or_sub_dimension=field,
                        old_value=serialize2String(old_value),
                        new_value=serialize2String(value),
                    )
                )

            if fr_logs:
                db.add_all(fr_logs)

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


def addFRBuildingGraphReport(
    user_id: int,
    fr_id: int,
    report: str,
) -> dict:
    """
    添加 FR 构建报告
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(report, str) or report.strip() == "":
        return {"status": -3, "message": "report cannot be empty"}

    with session() as db:
        fr = checkFigureAndRelationOwnership(db=db, user_id=user_id, fr_id=fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}

        report_item = FRBuildingGraphReport(
            fr_id=fr_id,
            report=report.strip(),
        )
        try:
            db.add(report_item)
            db.commit()
            db.refresh(report_item)
        except Exception as e:
            db.rollback()
            logger.error(f"Add FRBuildingGraphReport failed: {str(e)}")
            return {"status": -5, "message": "Add FRBuildingGraphReport failed"}

        return {
            "status": 200,
            "message": "Add FRBuildingGraphReport success",
            "fr_building_graph_report_id": report_item.id,
        }


def deleteFRBuildingGraphReport(
    user_id: int,
    fr_id: int,
    fr_building_graph_report_id: int,
) -> dict:
    """
    通过 report_id 软删除 FR 构建报告
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(fr_building_graph_report_id, int):
        return {"status": -3, "message": "Invalid fr_building_graph_report_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnership(db=db, user_id=user_id, fr_id=fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}

        try:
            report_item = (
                db.query(FRBuildingGraphReport)
                .filter(
                    FRBuildingGraphReport.id == fr_building_graph_report_id,
                    FRBuildingGraphReport.fr_id == fr_id,
                    FRBuildingGraphReport.is_deleted == False,
                )
                .first()
            )
            if report_item is None:
                return {"status": -5, "message": "FRBuildingGraphReport not found"}
            report_item.is_deleted = True
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Delete FRBuildingGraphReport failed: {str(e)}")
            return {"status": -6, "message": "Delete FRBuildingGraphReport failed"}

        return {"status": 200, "message": "Delete FRBuildingGraphReport success"}


def getFRBuildingGraphReport(
    user_id: int,
    fr_id: int,
    fr_building_graph_report_id: int,
) -> dict:
    """
    通过 report_id 获取 FR 构建报告详情
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(fr_building_graph_report_id, int):
        return {"status": -3, "message": "Invalid fr_building_graph_report_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnership(db=db, user_id=user_id, fr_id=fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}

        report_item = (
            db.query(FRBuildingGraphReport)
            .filter(
                FRBuildingGraphReport.id == fr_building_graph_report_id,
                FRBuildingGraphReport.fr_id == fr_id,
                FRBuildingGraphReport.is_deleted == False,
            )
            .first()
        )
        if report_item is None:
            return {"status": -5, "message": "FRBuildingGraphReport not found"}

        return {
            "status": 200,
            "message": "Get FRBuildingGraphReport success",
            "fr_building_graph_report": report_item.toJson(),
        }


def getAllFRBuildingGraphReport(
    user_id: int,
    fr_id: int,
) -> dict:
    """
    获取当前 fr 的全部构建报告（不包含详情字段裁剪）
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}

    with session() as db:
        fr = checkFigureAndRelationOwnership(db=db, user_id=user_id, fr_id=fr_id)
        if fr is None:
            return {"status": -3, "message": "FigureAndRelation not found"}

        report_items = (
            db.query(FRBuildingGraphReport)
            .filter(
                FRBuildingGraphReport.fr_id == fr_id,
                FRBuildingGraphReport.is_deleted == False,
            )
            .order_by(FRBuildingGraphReport.created_at.desc())
            .all()
        )
        return {
            "status": 200,
            "message": "Get all FRBuildingGraphReport success",
            "fr_building_graph_reports": [
                item.toJson(
                    include=[
                        "id",
                        "fr_id",
                        "report",
                        "is_deleted",
                        "created_at",
                    ]
                )
                for item in report_items
            ],
        }


def _normalizeValue(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _normalizeTextList(values: list[Any]) -> list[str]:
    normalized: list[str] = []
    for item in values:
        if item is None:
            continue
        text = str(item).strip()
        if text != "":
            normalized.append(text)
    return normalized


def _buildPersonaMarkdown(fr: FigureAndRelation) -> str:
    field_map: list[tuple[str, str]] = [
        ("figure_name", "姓名"),
        ("figure_gender", "性别"),
        ("figure_role", "角色"),
        ("figure_mbti", "MBTI"),
        ("figure_birthday", "生日"),
        ("figure_occupation", "职业"),
        ("figure_education", "教育背景"),
        ("figure_residence", "常住地"),
        ("figure_hometown", "家乡"),
        ("figure_likes", "喜好"),
        ("figure_dislikes", "不喜欢"),
        ("figure_appearance", "外在特征"),
        ("words_figure2user", "对用户常说的话"),
        ("words_user2figure", "用户常对TA说的话"),
        ("exact_relation", "精确关系"),
        ("core_personality", "核心性格与价值观"),
        ("core_interaction_style", "核心互动风格"),
        ("core_procedural_info", "核心程序性知识"),
        ("core_memory", "核心记忆"),
    ]
    lines = [f"# {fr.figure_name} 画像"]
    for field_name, title in field_map:
        value = getattr(fr, field_name, None)
        if value is None:
            continue
        if isinstance(value, str):
            text = value.strip()
            if text == "":
                continue
            lines.append(f"- {title}: {text}")
            continue
        if isinstance(value, list):
            text_list = _normalizeTextList(value)
            if not text_list:
                continue
            lines.append(f"- {title}: {'；'.join(text_list)}")
            continue
        lines.append(f"- {title}: {_normalizeValue(value)}")
    if len(lines) == 1:
        lines.append("- 暂无有效画像信息")
    return "\n".join(lines)


def _buildRecalledMarkdown(title: str, items: list[dict[str, Any]]) -> str:
    lines = [f"# {title}"]
    if not items:
        lines.append("- 无召回结果")
        return "\n".join(lines)
    for idx, item in enumerate(items, start=1):
        feed = item.get("fine_grained_feed", {}) or {}
        content = str(feed.get("content", "")).strip()
        if content == "":
            continue
        sub_dimension = str(feed.get("sub_dimension", "")).strip()
        confidence = feed.get("confidence")
        confidence_text = (
            _normalizeValue(confidence).strip() if confidence is not None else "unknown"
        )
        score = item.get("score", 0.0)
        try:
            score_text = f"{float(score):.4f}"
        except (TypeError, ValueError):
            score_text = "0.0000"
        if sub_dimension != "":
            lines.append(f"- [{idx}] {sub_dimension}: ")
        else:
            lines.append(f"- [{idx}] ")
        lines.append(f"  {content}")
    if len(lines) == 1:
        lines.append("- 无召回结果")
    return "\n".join(lines)


async def getFRAllContext(
    user_id: int,
    fr_id: int,
    query: str | None = None,
) -> dict:
    """
    获取当前 FigureAndRelation 全部相关上下文
    """
    if not isinstance(user_id, int):
        return {"status": -1, "message": "Invalid user_id"}
    if not isinstance(fr_id, int):
        return {"status": -2, "message": "Invalid fr_id"}
    if not isinstance(query, str) and query is not None:
        return {"status": -3, "message": "query must be a str"}
    with session() as db:
        fr = checkFigureAndRelationOwnership(db=db, user_id=user_id, fr_id=fr_id)
        if fr is None:
            return {"status": -4, "message": "FigureAndRelation not found"}
    persona = _buildPersonaMarkdown(fr)

    recalled_map = {
        "recalled_personality": None,
        "recalled_interaction_style": None,
        "recalled_procedural_info": None,
        "recalled_memory": None,
    }
    normalized_query = query.strip() if isinstance(query, str) else ""
    if normalized_query != "":
        dimension_conf = [
            {
                "result_key": "recalled_personality",
                "title": "性格与价值观",
                "dimension": FineGrainedFeedDimension.PERSONALITY,
                "top_k": 20,
            },
            {
                "result_key": "recalled_interaction_style",
                "title": "互动风格",
                "dimension": FineGrainedFeedDimension.INTERACTION_STYLE,
                "top_k": 10,
            },
            {
                "result_key": "recalled_procedural_info",
                "title": "程序性知识",
                "dimension": FineGrainedFeedDimension.PROCEDURAL_INFO,
                "top_k": 5,
            },
            {
                "result_key": "recalled_memory",
                "title": "人生记忆与故事",
                "dimension": FineGrainedFeedDimension.MEMORY,
                "top_k": 5,
            },
        ]
        for conf in dimension_conf:
            recall_res = await recallFineGrainedFeeds(
                user_id=user_id,
                fr_id=fr_id,
                query=normalized_query,
                top_k=conf["top_k"],
                scope=[conf["dimension"]],
            )
            if recall_res.get("status") != 200:
                return {
                    "status": -5,
                    "message": f"Recall FineGrainedFeed failed: {recall_res.get('message', '')}",
                }
            items = recall_res.get("items", [])
            recalled_map[conf["result_key"]] = (
                _buildRecalledMarkdown(title=conf["title"], items=items)
                if items
                else None
            )

    return {
        "status": 200,
        "message": "Get FigureAndRelation all context success",
        "persona": persona,
        "recalled_personality": recalled_map["recalled_personality"],
        "recalled_interaction_style": recalled_map["recalled_interaction_style"],
        "recalled_procedural_info": recalled_map["recalled_procedural_info"],
        "recalled_memory": recalled_map["recalled_memory"],
    }
