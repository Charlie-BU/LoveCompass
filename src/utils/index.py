from datetime import datetime, timezone
from enum import Enum
import json
import math
import os
from typing import Any
from sqlalchemy.orm import Session

from src.database.models import FigureAndRelation, OriginalSource


def timeDecay(created_at: datetime) -> float:
    """
    时间衰减函数
    """
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    delta_days = (now - created_at).days

    return math.exp(-delta_days / int(os.getenv("HALF_LIFE_DAYS")))


def checkFigureAndRelationOwnership(
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


def checkOriginalSourceOwnership(
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


def cleanList(items: list):
    """
    清理列表中的重复字符串项，保留首次出现的项。
    参数:
    items (list): 包含字符串的列表。
    返回:
    list: 清理后的列表，仅包含唯一的非空字符串项。
    """
    if isinstance(items, list):
        raw_items = items
    elif isinstance(items, str):
        raw_items = [items]
    else:
        raw_items = []
    seen = set()
    result = []
    for item in raw_items:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if normalized == "" or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def stringifyValue(value: Any, strip: bool = True) -> str:
    """
    文本化，支持 enum、List[str|dict]、None 等类型。
    """

    def _normalizeString(text: str) -> str:
        return text.strip() if strip else text

    if value is None:
        return ""
    if hasattr(value, "value"):
        return _normalizeString(str(value.value))
    if isinstance(value, str):
        return _normalizeString(value)
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = stringifyValue(item.get("text"), strip=strip)
                if text != "":
                    parts.append(text)
            elif isinstance(item, str):
                text = stringifyValue(item, strip=strip)
                if text != "":
                    parts.append(text)
        return "\n".join(parts)
    try:
        return _normalizeString(str(value))
    except Exception:
        return ""


def serialize2String(value: Any) -> str | None:
    """
    将 str/list/dict/enum 等不同类型的值序列化为字符串
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, (list, dict)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=lambda x: x.value if isinstance(x, Enum) else str(x),
        )
    return str(value)


def jsonDefault(obj):
    """
    自定义 JSON 序列化函数，处理 Enum 和 datetime 类型
    """
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)
