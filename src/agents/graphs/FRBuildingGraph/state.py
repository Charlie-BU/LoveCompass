from typing import Annotated, Any, Literal, TypedDict

from src.database.enums import (
    FigureRole,
    FineGrainedFeedConfidence,
    FineGrainedFeedDimension,
    MBTI,
    OriginalSourceType,
)


class Request(TypedDict, total=False):
    user_id: int
    fr_id: int
    raw_content: str    # 原始文本内容
    raw_images: list[str] | None    # 原始图片url


class OriginalSourceTemp(TypedDict, total=False):
    type: OriginalSourceType
    confidence: FineGrainedFeedConfidence
    included_dimensions: list[FineGrainedFeedDimension]
    content: str
    approx_date: str | None


class FRIntrinsicUpdates(TypedDict, total=False):
    figure_mbti: MBTI | None
    figure_birthday: str
    figure_occupation: str
    figure_education: str
    figure_residence: str
    figure_hometown: str
    figure_appearance: str
    figure_likes: list[str]
    figure_dislikes: list[str]
    words_figure2user: list[str]
    words_user2figure: list[str]
    exact_relation: str


class ExtractedFineGrainedFeed(TypedDict, total=False):
    dimension: FineGrainedFeedDimension
    sub_dimension: str | None
    content: str
    confidence: FineGrainedFeedConfidence


class RecalledFineGrainedFeed(TypedDict, total=False):
    id: int
    dimension: FineGrainedFeedDimension
    sub_dimension: str | None
    confidence: FineGrainedFeedConfidence
    content: str
    score: float


class FeedUpsertPlanItem(TypedDict, total=False):
    extracted_feed: ExtractedFineGrainedFeed
    action: Literal["add", "update", "skip", "conflict"]
    target_feed_id: int | None
    merged_content: str | None
    reason: str
    recalled_candidates: list[RecalledFineGrainedFeed]


class NodeLog(TypedDict, total=False):
    step: str
    status: Literal["ok", "skip", "error"]
    detail: str
    data: dict[str, Any]


def _mergeUniqueList(left: list[Any], right: list[Any]) -> list[Any]:
    """
    合并并去重列表，兼容并行分支同时写同一 channel 的场景
    """
    merged = []
    for item in (left or []) + (right or []):
        if item in merged:
            continue
        merged.append(item)
    return merged


class FRBuildingGraphState(TypedDict, total=False):
    request: Request
    figure_and_relation: dict[str, Any]
    figure_role: FigureRole
    role_recipe_path: str
    conflict_recipe_path: str
    original_source: OriginalSourceTemp
    original_source_id: int
    fr_intrinsic_updates: FRIntrinsicUpdates
    fr_update_result: dict[str, Any]
    extracted_feeds: list[ExtractedFineGrainedFeed]
    feed_upsert_plan: list[FeedUpsertPlanItem]
    feed_upsert_results: list[dict[str, Any]]
    logs: Annotated[list[NodeLog], _mergeUniqueList]
    warnings: Annotated[list[str], _mergeUniqueList]
    errors: Annotated[list[str], _mergeUniqueList]
    status: Literal["running", "failed", "completed"]
    fr_building_report: str | None


class FRBuildingGraphInput(TypedDict, total=False):
    request: Request


class FRBuildingGraphOutput(TypedDict, total=False):
    status: int
    message: str
    original_source_id: int | None
    fr_update_result: dict[str, Any] | None
    feed_upsert_results: list[dict[str, Any]]
    logs: list[NodeLog]
    warnings: list[str]
    errors: list[str]
    fr_building_report: str | None
