from datetime import datetime, timezone
from enum import Enum
import json
import math
import os
from typing import Any, Awaitable, Callable, TypeVar
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.orm import Session
import asyncio
import threading

from src.database.models import FigureAndRelation, OriginalSource

# todo: 待治理：模块顶层引入太多依赖，不是纯 utils

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


def parseInt(value: Any):
    """
    尝试将值转换为整数，返回 None 如果转换失败。
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parseFloat(value: Any):
    """
    尝试将值转换为浮点数，返回 None 如果转换失败。
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    将 str/list/dict/enum 等不同类型的值序列化为 json 字符串
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


T = TypeVar("T")


def runAwaitableSync(awaitable_factory: Callable[..., Awaitable[T]]) -> T:
    """
    同步运行异步函数
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable_factory())

    result_box: dict[str, T] = {}
    error_box: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result_box["value"] = asyncio.run(awaitable_factory())
        except BaseException as err:  # pragma: no cover - propagated to caller
            error_box["error"] = err

    worker = threading.Thread(target=_runner, daemon=True)
    worker.start()
    worker.join()

    if "error" in error_box:
        raise error_box["error"]
    return result_box["value"]


async def ainvokeJsonWithRetry(
    messages: list[BaseMessage],
    invoke_content: Callable[[list[BaseMessage]], Awaitable[str]],
    correction_hint: str | None = None,
    max_retries: int = 1,
) -> tuple[Any, str]:
    """
    调用 LLM 并解析 JSON；若解析失败，自动追加 AIMessage + HumanMessage 后重试。
    返回最后一次 (parsed_json, raw_content)。
    """
    if max_retries < 0:
        max_retries = 0

    retry_messages = list(messages)
    default_hint = (
        "你上一条输出不是合法 JSON。"
        "请严格按原任务要求重新输出，且仅输出可被 json.loads 解析的 JSON 对象。"
        "不要包含 markdown、代码块标记或额外解释。"
        "特别注意引号使用：JSON 的 key 必须使用英文双引号，"
        "字符串值也必须使用英文双引号并在必要处正确转义；"
        "禁止使用单引号、中文引号或未转义的双引号。"
    )
    hint = correction_hint or default_hint
    last_raw_content = ""

    for attempt in range(max_retries + 1):
        last_raw_content = stringifyValue(
            await invoke_content(retry_messages), strip=False
        )
        try:
            return json.loads(last_raw_content), last_raw_content
        except json.JSONDecodeError:
            if attempt >= max_retries:
                break
            retry_messages = retry_messages + [
                AIMessage(content=last_raw_content),
                HumanMessage(content=hint),
            ]

    raise ValueError("LLM response is not valid JSON")
