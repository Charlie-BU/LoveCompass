import json
import logging
import os
import pprint
from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.graphs.FRBuildingGraph.state import FRBuildingGraphState
from src.agents.llm import prepareLLM
from src.agents.prompt import getPrompt
from src.database.enums import (
    ConflictStatus,
    FigureRole,
    FineGrainedFeedConfidence,
    FineGrainedFeedDimension,
    MBTI,
    OriginalSourceType,
    parseEnum,
)
from src.database.index import session
from src.services.figure_and_relation import (
    fr_allowed_fields,
    fr_list_fields,
    fr_string_fields,
    updateFigureAndRelation,
)
from src.services.fine_grained_feed import addOriginalSource
from src.utils.index import (
    checkFigureAndRelationOwnership,
    cleanList,
    normalizeText,
)

logger = logging.getLogger(__name__)


async def _compareFieldViaLLM(
    field_name: str,
    field_type: Literal["string", "list"],
    old_value: str,
    new_value: str,
) -> dict:
    """
    通过 LLM 对照字段值，返回冲突状态和冲突详情
    """
    llm = prepareLLM(
        "DOUBAO_2_0_MINI",
        options={
            "temperature": 0,
            "reasoning_effort": "minimal",
        },
    )
    FR_BUILDING_COMPARE_FIELD = await getPrompt(os.getenv("FR_BUILDING_COMPARE_FIELD"))
    # 提示词兜底
    if not FR_BUILDING_COMPARE_FIELD:
        logger.error("FR compare field prompt is empty")
        raise ValueError("FR compare field prompt is empty")

    user_prompt = f"field_name: {field_name}\n\nfield_type: {field_type}\n\nold_value: {old_value}\n\nnew_value: {new_value}"
    response = await llm.ainvoke(
        [
            SystemMessage(content=FR_BUILDING_COMPARE_FIELD),
            HumanMessage(content=user_prompt),
        ]
    )
    try:
        parsed_res = json.loads(response.content)
    except json.JSONDecodeError:
        logger.error("LLM response is not valid JSON")
        raise ValueError("LLM response is not valid JSON")

    return {
        "final_value": parsed_res.get("final_value"),
        "conflict_status": parseEnum(ConflictStatus, parsed_res.get("conflict_status")),
        "detail": parsed_res.get("detail"),
    }


# 步骤 1-3
def nodeLoadFR(state: FRBuildingGraphState) -> dict:
    """
    加载当前 figure_and_relation 和 figure_role
    """
    request = state["request"]
    with session() as db:
        figure_and_relation = checkFigureAndRelationOwnership(
            db=db, user_id=request["user_id"], fr_id=request["fr_id"]
        )
        if figure_and_relation is None:
            logger.error("Figure and relation not found")
            raise ValueError("Figure and relation not found")
        # 追加节点执行日志，保留上游日志链路
        logs = state.get("logs") or []
        logs += [
            {
                "step": "nodeLoadFR",
                "status": "ok",
                "detail": "FigureAndRelation loaded",
                "data": {
                    "fr_id": request["fr_id"],
                    "figure_role": figure_and_relation.figure_role,
                },
            }
        ]
        return {
            "figure_and_relation": figure_and_relation.toJson(),
            "figure_role": parseEnum(FigureRole, figure_and_relation.figure_role),
            "logs": logs,
        }


# 步骤 4
async def nodePreprocessInput(state: FRBuildingGraphState) -> dict:
    """
    预处理 raw_content 和 raw_images（如有）
    """
    request = state["request"]
    raw_content = (request.get("raw_content") or "").strip()
    raw_images = request.get("raw_images") or []
    # warnings / logs 统一通过 state 透传，保证可观测性
    warnings = state.get("warnings") or []
    logs = state.get("logs") or []

    # 空判定
    if raw_content == "" and len(raw_images) == 0:
        logger.error("raw_content and raw_images cannot be both empty")
        raise ValueError("raw_content and raw_images cannot be both empty")
    # 内容过短
    if raw_content and len(raw_content) < 10:
        warning = "raw_content is too short, it may not contain enough information"
        logger.warning(warning)
        # 保留为 warning，中断流程
        warnings = warnings + [warning]
        raise ValueError(warning)

    # LLM 预处理
    llm = prepareLLM(
        "DOUBAO_2_0_MINI",
        options={
            "temperature": 0,
            "reasoning_effort": "low",
        },
    )
    FR_BUILDING_PREPROCESS = await getPrompt(os.getenv("FR_BUILDING_PREPROCESS"))
    # 提示词兜底
    if not FR_BUILDING_PREPROCESS:
        logger.error("FR preprocess prompt is empty")
        raise ValueError("FR preprocess prompt is empty")

    user_prompt = (
        f"[figure_role]:\n{state['figure_role'].value}\n\n[raw_content]:\n{raw_content}"
    )
    if raw_images:
        user_prompt = [{"type": "text", "text": user_prompt}] + [
            {"type": "image_url", "image_url": {"url": url}} for url in raw_images
        ]

    messages = [
        SystemMessage(content=FR_BUILDING_PREPROCESS),
        HumanMessage(content=user_prompt),
    ]
    response = await llm.ainvoke(messages)
    try:
        parsed_res = json.loads(response.content)
    except json.JSONDecodeError:
        logger.error("LLM response is not valid JSON")
        raise ValueError("LLM response is not valid JSON")

    # logger.info(json.dumps(parsed_res, ensure_ascii=False, indent=2))
    cleaned_content = parsed_res.get("cleaned_content", "")
    metadata = parsed_res.get("metadata", {})

    # 格式兜底
    if cleaned_content.strip() == "":
        warning = "cleaned_content is empty after preprocessing"
        logger.warning(warning)
        warnings = warnings + [warning]
    if not metadata.get("included_dimensions"):
        warning = "included_dimensions is empty, fallback to [other]"
        logger.warning(warning)
        warnings = warnings + [warning]

    original_source = {
        "content": cleaned_content,
        "type": parseEnum(OriginalSourceType, metadata.get("original_source_type")),
        "confidence": parseEnum(
            FineGrainedFeedConfidence, metadata.get("confidence", "")
        ),
        "included_dimensions": [
            parseEnum(FineGrainedFeedDimension, dim)
            for dim in metadata.get("included_dimensions", [])
        ]
        # 维度缺失时兜底，避免 addOriginalSource 参数校验失败
        or [FineGrainedFeedDimension.OTHER],
        "approx_date": metadata.get("approx_date"),
    }

    # 追加当前节点日志，用于后续返回给消费方
    logs += [
        {
            "step": "nodePreprocessInput",
            "status": "ok",
            "detail": "Input preprocessed and original source prepared",
            "data": {
                "type": original_source["type"].value,
                "confidence": original_source["confidence"].value,
                "included_dimensions": [
                    dim.value for dim in original_source["included_dimensions"]
                ],
                "has_raw_images": len(raw_images) > 0,
                "raw_content_length": len(raw_content),
                "cleaned_content_length": len(cleaned_content),
            },
        }
    ]

    return {
        "original_source": original_source,
        "warnings": warnings,
        "logs": logs,
    }


def nodePersistOriginalSource(state: FRBuildingGraphState) -> dict:
    """
    original_source 落库
    """
    original_source = state["original_source"]
    res = addOriginalSource(
        user_id=state["request"]["user_id"],
        fr_id=state["request"]["fr_id"],
        **original_source,
    )
    if res["status"] != 200:
        logger.error(res.get("message", "Add original source failed"))
        raise ValueError("Add original source failed")

    logs = state.get("logs") or []
    warnings = state.get("warnings") or []
    original_source_id = res.get("original_source_id")

    # 持久化完成后记录服务返回，方便排查链路问题
    logs += [
        {
            "step": "nodePersistOriginalSource",
            "status": "ok",
            "detail": "Original source persisted",
            "data": {
                "service_status": res.get("status"),
                "service_message": res.get("message"),
                "original_source_id": original_source_id,
            },
        }
    ]

    return {
        "original_source_id": original_source_id,
        "warnings": warnings,
        "logs": logs,
    }


# 步骤 5
async def nodeExtractFRIntrinsicCandidates(state: FRBuildingGraphState) -> dict:
    """
    从 original_source 中提取 FR 内在字段
    """
    warnings = state.get("warnings") or []
    logs = state.get("logs") or []

    original_source = state.get("original_source") or {}
    original_source_content = (original_source.get("content") or "").strip()
    if original_source_content == "":
        warning = "original_source.content is empty"
        logger.warning(warning)
        warnings = warnings + [warning]
        raise ValueError(f"FR intrinsic extraction failed, {warning}")

    FR_BUILDING_EXTRACT_FR_INTRINSIC_CANDIDATES = await getPrompt(
        os.getenv("FR_BUILDING_EXTRACT_FR_INTRINSIC_CANDIDATES")
    )
    # 提示词兜底
    if not FR_BUILDING_EXTRACT_FR_INTRINSIC_CANDIDATES:
        logger.error("FR intrinsic extraction prompt is empty")
        raise ValueError("FR intrinsic extraction prompt is empty")

    user_prompt = f"[figure_role]:\n{state['figure_role'].value}\n\n[original_source_content]:\n{original_source_content}"
    llm = prepareLLM(
        "DOUBAO_2_0_LITE",
        options={
            "temperature": 0,
            "reasoning_effort": "low",
        },
    )
    response = await llm.ainvoke(
        [
            SystemMessage(content=FR_BUILDING_EXTRACT_FR_INTRINSIC_CANDIDATES),
            HumanMessage(content=user_prompt),
        ]
    )

    try:
        parsed_res = json.loads(response.content)
    except json.JSONDecodeError:
        logger.error("LLM response is not valid JSON")
        raise ValueError("LLM response is not valid JSON")

    raw_candidates = parsed_res.get("fr_intrinsic_candidates")

    if not isinstance(raw_candidates, dict):
        warning = "fr_intrinsic_candidates is not a dict, fallback to empty updates"
        logger.warning(warning)
        warnings = warnings + [warning]
        raw_candidates = {}

    # 将 raw_candidates 中的字段转换为 FR 合法字段类型
    fr_intrinsic_updates = {}
    ignored_fields = []  # 非 FR 合法字段，用于日志记录
    for field, value in raw_candidates.items():
        if field not in fr_allowed_fields:
            ignored_fields.append(field)
            continue
        if value is None:
            continue

        if field == "figure_mbti":
            if isinstance(value, str) and value.strip() != "":
                try:
                    fr_intrinsic_updates[field] = parseEnum(MBTI, value.strip().upper())
                except Exception:
                    warning = f"Invalid figure_mbti extracted: {value}"
                    logger.warning(warning)
                    warnings = warnings + [warning]
            continue

        if field in fr_list_fields:
            normalized_list = []
            if isinstance(value, list):
                normalized_list = [
                    item.strip()
                    for item in value
                    if isinstance(item, str) and item.strip() != ""
                ]
            elif isinstance(value, str) and value.strip() != "":
                normalized_list = [value.strip()]
            else:
                warning = f"Invalid list field extracted for {field}"
                logger.warning(warning)
                warnings = warnings + [warning]
            if normalized_list:
                # 去重（是不是有点过度设计了？）
                seen = set()
                deduped = []
                for item in normalized_list:
                    if item in seen:
                        continue
                    seen.add(item)
                    deduped.append(item)
                fr_intrinsic_updates[field] = deduped
            continue

        if field in fr_string_fields(detailed=False):
            if isinstance(value, str):
                normalized_value = value.strip()
                if normalized_value != "":
                    fr_intrinsic_updates[field] = normalized_value
            else:
                warning = f"Invalid string field extracted for {field}"
                logger.warning(warning)
                warnings = warnings + [warning]

    logs += [
        {
            "step": "nodeExtractFRIntrinsicCandidates",
            "status": "ok",
            "detail": "FR intrinsic candidates extracted and normalized",
            "data": {
                "extracted_fields": sorted(fr_intrinsic_updates.keys()),
                "extracted_count": len(fr_intrinsic_updates),
                "ignored_fields": sorted(ignored_fields),
            },
        }
    ]

    pprint.pprint(fr_intrinsic_updates, indent=2)
    return {
        "fr_intrinsic_updates": fr_intrinsic_updates,
        "warnings": warnings,
        "logs": logs,
    }


async def nodePlanFRIntrinsicUpdate(state: FRBuildingGraphState) -> dict:
    """
    FR 内在字段对照更新
    """
    warnings = state.get("warnings") or []
    logs = state.get("logs") or []
    figure_and_relation = state.get("figure_and_relation") or {}
    extracted_candidates = state.get("fr_intrinsic_updates") or {}

    if not isinstance(extracted_candidates, dict) or len(extracted_candidates) == 0:
        logs += [
            {
                "step": "nodePlanFRIntrinsicUpdate",
                "status": "skip",
                "detail": "No extracted FR intrinsic candidates to plan",
                "data": {},
            }
        ]
        return {"fr_intrinsic_updates": {}, "warnings": warnings, "logs": logs}

    def _normalizeMBTI(value: MBTI | str) -> MBTI | None:
        """
        归一化 MBTI 字段
        """
        if isinstance(value, MBTI):
            return value
        if isinstance(value, str) and value.strip() != "":
            try:
                return parseEnum(MBTI, value.strip().upper())
            except Exception:
                return None
        return None

    planned_updates = {}
    plan_actions = []  # 用于日志记录

    # 逐一处理每个抽取的字段
    for field, new_value in extracted_candidates.items():
        # MBTI 字段，单独处理
        if field == "figure_mbti":
            # 无需模型对照
            existing_mbti = _normalizeMBTI(figure_and_relation.get(field))
            new_mbti = _normalizeMBTI(new_value)
            if new_mbti is None:
                continue
            if existing_mbti is None:
                planned_updates[field] = new_mbti
                plan_actions.append(
                    {"field": field, "action": ConflictStatus.RESOLVED_ACCEPT_NEW.value}
                )
                continue
            if existing_mbti == new_mbti:
                plan_actions.append(
                    {"field": field, "action": ConflictStatus.RESOLVED_KEEP_OLD.value}
                )
                continue
            # MBTI 变化：记录后直接替换
            planned_updates[field] = new_mbti
            warning = (
                f"FR intrinsic conflict on {field}, replace "
                f"{existing_mbti.value} -> {new_mbti.value}"
            )
            logger.warning(warning)
            warnings = warnings + [warning]
            plan_actions.append(
                {"field": field, "action": ConflictStatus.RESOLVED_ACCEPT_NEW.value}
            )
            continue

        # list 类型字段
        if field in fr_list_fields:
            existing_list = cleanList(figure_and_relation.get(field))
            new_list = cleanList(new_value)
            if len(new_list) == 0:
                # 新值为空，直接跳过
                continue
            if len(existing_list) == 0:
                # 旧值为空，直接填充新值
                planned_updates[field] = new_list
                plan_actions.append(
                    {"field": field, "action": ConflictStatus.RESOLVED_ACCEPT_NEW.value}
                )
                continue
            elif new_list == existing_list:
                # 新旧值完全相等，直接跳过
                plan_actions.append(
                    {"field": field, "action": ConflictStatus.RESOLVED_KEEP_OLD.value}
                )
                continue
            # 递交模型判断
            LLM_compare_res = await _compareFieldViaLLM(
                field_name=field,
                field_type="list",
                old_value=json.dumps(existing_list),
                new_value=json.dumps(new_list),
            )
            # 对于 FR 内在字段判断，直接更新，无需考虑冲突落库
            final_value = list(LLM_compare_res.get("final_value"))
            planned_updates[field] = final_value
            plan_actions.append(
                {
                    "field": field,
                    "action": LLM_compare_res.get("conflict_status").value,
                    "detail": LLM_compare_res.get("detail"),
                }
            )
            continue

        # string 类型字段
        if field in fr_string_fields(detailed=False):
            existing_text = normalizeText(figure_and_relation.get(field))
            new_text = normalizeText(new_value)
            if new_text == "":
                # 新值为空，直接跳过
                continue
            if existing_text == "":
                # 旧值为空，直接填充新值
                planned_updates[field] = new_text
                plan_actions.append(
                    {"field": field, "action": ConflictStatus.RESOLVED_ACCEPT_NEW.value}
                )
                continue
            elif new_text == existing_text:
                # 新旧值完全相等，直接跳过
                plan_actions.append(
                    {"field": field, "action": ConflictStatus.RESOLVED_KEEP_OLD.value}
                )
                continue

            # 递交模型判断
            LLM_compare_res = await _compareFieldViaLLM(
                field_name=field,
                field_type="string",
                old_value=existing_text,
                new_value=new_text,
            )
            # 对于 FR 内在字段判断，直接更新，无需考虑冲突落库
            planned_updates[field] = LLM_compare_res.get("final_value")
            plan_actions.append(
                {
                    "field": field,
                    "action": LLM_compare_res.get("conflict_status").value,
                    "detail": LLM_compare_res.get("detail"),
                }
            )

    logs += [
        {
            "step": "nodePlanFRIntrinsicUpdate",
            "status": "ok",
            "detail": "FR intrinsic update planned",
            "data": {
                "planned_fields": sorted(planned_updates.keys()),
                "planned_count": len(planned_updates),
                "plan_actions": plan_actions,
            },
        }
    ]

    return {"fr_intrinsic_updates": planned_updates, "warnings": warnings, "logs": logs}


def nodePersistFRIntrinsicUpdate(state: FRBuildingGraphState) -> dict:
    """
    FR 内在字段更新落库
    """
    request = state["request"]
    warnings = state.get("warnings") or []
    logs = state.get("logs") or []
    fr_intrinsic_updates = state.get("fr_intrinsic_updates") or {}

    if not isinstance(fr_intrinsic_updates, dict) or len(fr_intrinsic_updates) == 0:
        logs += [
            {
                "step": "nodePersistFRIntrinsicUpdate",
                "status": "skip",
                "detail": "No FR intrinsic updates to persist",
                "data": {},
            }
        ]
        return {
            "fr_update_result": {"status": 200, "message": "No FR intrinsic updates"},
            "warnings": warnings,
            "logs": logs,
        }

    res = updateFigureAndRelation(
        user_id=request["user_id"],
        fr_id=request["fr_id"],
        fr_body=fr_intrinsic_updates,
    )
    if res.get("status") != 200:
        logger.error(res.get("message", "Update FigureAndRelation failed"))
        raise ValueError(res.get("message", "Update FigureAndRelation failed"))

    figure_and_relation = dict(state.get("figure_and_relation") or {})
    figure_and_relation.update(fr_intrinsic_updates)

    logs += [
        {
            "step": "nodePersistFRIntrinsicUpdate",
            "status": "ok",
            "detail": "FR intrinsic updates persisted",
            "data": {
                "service_status": res.get("status"),
                "service_message": res.get("message"),
                "updated_fields": sorted(fr_intrinsic_updates.keys()),
                "updated_count": len(fr_intrinsic_updates),
            },
        }
    ]

    return {
        "fr_update_result": {
            "status": res.get("status"),
            "message": res.get("message"),
            "updated_fields": sorted(fr_intrinsic_updates.keys()),
            "updated_count": len(fr_intrinsic_updates),
        },
        "figure_and_relation": figure_and_relation,
        "warnings": warnings,
        "logs": logs,
    }
