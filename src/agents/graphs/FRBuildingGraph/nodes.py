import asyncio
import json
import logging
import os
from typing import List, Literal
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.graphs.FRBuildingGraph.state import (
    ExtractedFineGrainedFeed,
    FRBuildingGraphOutput,
    FRBuildingGraphState,
)
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
    addFRBuildingGraphReport,
    fr_allowed_fields,
    fr_list_fields,
    fr_string_fields,
    updateFigureAndRelation,
)
from src.services.fine_grained_feed import (
    addFineGrainedFeed,
    addFineGrainedFeedConflict,
    addOriginalSource,
    recallFineGrainedFeeds,
    updateFineGrainedFeed,
)
from src.utils.index import (
    checkFigureAndRelationOwnership,
    cleanList,
    jsonDefault,
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
        "tag": parsed_res.get("tag"),
        "final_value": parsed_res.get("final_value"),
        "conflict_status": parseEnum(ConflictStatus, parsed_res.get("conflict_status")),
        "detail": parsed_res.get("detail"),
    }


# 步骤 1-3
def nodeLoadFR(state: FRBuildingGraphState) -> dict:
    """
    加载当前 figure_and_relation 和 figure_role
    """
    logger.info("nodeLoadFR is called")
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
        logger.info("nodeLoadFR executed finished\n")
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
    logger.info("nodePreprocessInput is called")
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
        "DOUBAO_2_0_LITE",
        options={
            "temperature": 0,
            "reasoning_effort": "minimal",
        },
    )   # todo：参数 TBD
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
    print(f"\n{response.content}\n")
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

    logger.info("nodePreprocessInput executed finished\n")
    return {
        "original_source": original_source,
        "warnings": warnings,
        "logs": logs,
    }


def nodePersistOriginalSource(state: FRBuildingGraphState) -> dict:
    """
    original_source 落库
    """
    logger.info("nodePersistOriginalSource is called")
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

    logger.info("nodePersistOriginalSource executed finished\n")
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
    logger.info("nodeExtractFRIntrinsicCandidates is called")
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

    logger.info(
        f"fr_intrinsic_updates: \n{json.dumps(fr_intrinsic_updates, ensure_ascii=False, indent=2, default=jsonDefault)}\n"
    )
    logger.info("nodeExtractFRIntrinsicCandidates executed finished\n")
    return {
        "fr_intrinsic_updates": fr_intrinsic_updates,
        "warnings": warnings,
        "logs": logs,
    }


async def nodePlanFRIntrinsicUpdate(state: FRBuildingGraphState) -> dict:
    """
    FR 内在字段对照更新计划
    """
    logger.info("nodePlanFRIntrinsicUpdate is called")
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
        logger.info("nodePlanFRIntrinsicUpdate executed finished\n")
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

    logger.info("nodePlanFRIntrinsicUpdate executed finished\n")
    return {"fr_intrinsic_updates": planned_updates, "warnings": warnings, "logs": logs}


def nodePersistFRIntrinsicUpdate(state: FRBuildingGraphState) -> dict:
    """
    FR 内在字段更新落库
    """
    logger.info("nodePersistFRIntrinsicUpdate is called")
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
        logger.info("nodePersistFRIntrinsicUpdate executed finished\n")
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

    logger.info("nodePersistFRIntrinsicUpdate executed finished\n")
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


# 步骤 6
async def nodeExtractFineGrainedFeeds(state: FRBuildingGraphState) -> dict:
    """
    从 original_source 中提取细粒度信息
    """
    logger.info("nodeExtractFineGrainedFeeds is called")
    warnings = state.get("warnings") or []
    logs = state.get("logs") or []

    # 获取元数据
    figure_role = state.get("figure_role")
    original_source = state.get("original_source") or {}
    original_source_content = (original_source.get("content") or "").strip()
    included_dimensions = original_source.get("included_dimensions") or []
    default_confidence = original_source.get("confidence")

    if not isinstance(figure_role, FigureRole):
        logger.error("figure_role is invalid")
        raise ValueError("figure_role is invalid")
    if original_source_content == "":
        warning = "original_source.content is empty"
        logger.warning(warning)
        warnings = warnings + [warning]
        raise ValueError(f"FineGrainedFeed extraction failed, {warning}")
    if not isinstance(included_dimensions, list):
        included_dimensions = []
    if not default_confidence:
        warning = "original_source.confidence is empty"
        logger.warning(warning)
        warnings = warnings + [warning]
        raise ValueError(f"FineGrainedFeed extraction failed, {warning}")

    # 获取 role prompt
    role_prompt_key = f"FR_BUILDING_{figure_role.value.upper()}"
    role_prompt = await getPrompt(os.getenv(role_prompt_key))
    if not role_prompt:
        warning = f"Prompt is empty: {role_prompt_key}"
        logger.warning(warning)
        warnings = warnings + [warning]
        raise ValueError(f"FineGrainedFeed extraction failed, {warning}")

    # 获取所需的全部 dimension prompts
    if len(included_dimensions) == 0:
        warning = "No dimensions to extract"
        logger.warning(warning)
        warnings = warnings + [warning]
        logger.info("nodeExtractFineGrainedFeeds executed finished\n")
        return {"warnings": warnings, "logs": logs}

    dimension_prompt_pair = []
    for dimension in included_dimensions:
        if not isinstance(dimension, FineGrainedFeedDimension):
            warning = f"Invalid included_dimension: {dimension}"
            logger.warning(warning)
            warnings = warnings + [warning]
            continue
        dimension_prompt_key = f"FR_BUILDING_{dimension.value.upper()}"
        dimension_prompt = await getPrompt(os.getenv(dimension_prompt_key))
        if not dimension_prompt:
            warning = f"Prompt is empty: {dimension_prompt_key}"
            logger.warning(warning)
            warnings = warnings + [warning]
            continue
        dimension_prompt_pair.append((dimension, dimension_prompt))

    # LLM 抽取
    llm = prepareLLM(
        "DOUBAO_2_0_LITE",
        options={
            "temperature": 0,
            "reasoning_effort": "low",
        },
    )
    user_prompt = original_source_content

    async def _extractByDimension(
        dimension: FineGrainedFeedDimension,
        dimension_prompt: str,
    ) -> tuple[FineGrainedFeedDimension, list[dict], str | None]:
        """
        按维度提取细粒度信息
        """
        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content=role_prompt),
                    SystemMessage(content=dimension_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
        except Exception as e:
            return dimension, [], f"LLM invoke failed: {str(e)}"

        try:
            raw_feeds = json.loads(response.content)
        except Exception:
            return dimension, [], "LLM response is not valid JSON"
        if not isinstance(raw_feeds, list):
            return dimension, [], "LLM response is not valid JSON"

        feeds: List[ExtractedFineGrainedFeed] = []
        for raw_item in raw_feeds:
            if not isinstance(raw_item, dict):
                continue
            confidence = parseEnum(
                FineGrainedFeedConfidence, raw_item.get("confidence")
            )
            if not confidence:
                confidence = default_confidence
            sub_dimension = raw_item.get("sub_dimension") or ""
            content = raw_item.get("content") or ""
            if content == "":
                continue
            feeds.append(
                ExtractedFineGrainedFeed(
                    dimension=dimension,
                    sub_dimension=sub_dimension,
                    content=content,
                    confidence=confidence,
                )
            )

        return dimension, feeds, None

    tasks = []
    for dimension, dimension_prompt in dimension_prompt_pair:
        tasks.append(_extractByDimension(dimension, dimension_prompt))

    res: List[tuple[FineGrainedFeedDimension, list[dict], str | None]] = (
        await asyncio.gather(*tasks)
    )
    extracted_feeds = []
    extract_errors = []
    for res_each in res:
        dimension, feeds, error = res_each
        if error:
            warning = f"{dimension.value} extraction failed: {error}"
            logger.warning(warning)
            warnings = warnings + [warning]
            extract_errors.append({"dimension": dimension.value, "error": error})
            continue
        extracted_feeds.extend(feeds)

    logs += [
        {
            "step": "nodeExtractFineGrainedFeeds",
            "status": "ok",
            "detail": "FineGrainedFeed candidates extracted",
            "data": {
                "role_prompt_key": role_prompt_key,
                "included_dimensions": [
                    dim.value
                    for dim in included_dimensions
                    if isinstance(dim, FineGrainedFeedDimension)
                ],
                "prompt_task_count": len(tasks),
                "extract_errors": extract_errors,
            },
        }
    ]

    logger.info("nodeExtractFineGrainedFeeds executed finished\n")
    return {
        "extracted_feeds": extracted_feeds,
        "warnings": warnings,
        "logs": logs,
    }


async def nodePlanFineGrainedFeedUpsert(state: FRBuildingGraphState) -> dict:
    """
    FineGrainedFeed 对照更新计划
    """
    logger.info("nodePlanFineGrainedFeedUpsert is called")
    warnings = state.get("warnings") or []
    logs = state.get("logs") or []
    request = state.get("request") or {}
    extracted_feeds = state.get("extracted_feeds") or []

    user_id = request.get("user_id")
    fr_id = request.get("fr_id")
    if not isinstance(user_id, int) or not isinstance(fr_id, int):
        logger.error("Invalid request.user_id or request.fr_id")
        raise ValueError("Invalid request.user_id or request.fr_id")

    if not isinstance(extracted_feeds, list) or len(extracted_feeds) == 0:
        logs += [
            {
                "step": "nodePlanFineGrainedFeedUpsert",
                "status": "skip",
                "detail": "No extracted feeds to plan",
                "data": {},
            }
        ]
        logger.info("nodePlanFineGrainedFeedUpsert executed finished\n")
        return {
            "feed_upsert_plan": [],
            "warnings": warnings,
            "logs": logs,
        }

    # 召回条数限制在 3-5，默认 3
    top_k = int(os.getenv("FR_BUILDING_FEED_RECALL_TOP_K") or 3)

    feed_upsert_plan = []
    for feed in extracted_feeds:
        if not isinstance(feed, dict):
            warning = f"Invalid extracted feed item: {feed}"
            logger.warning(warning)
            warnings = warnings + [warning]
            continue

        dimension = feed.get("dimension")
        content = normalizeText(feed.get("content"))
        if not isinstance(dimension, FineGrainedFeedDimension):
            warning = f"Invalid extracted feed dimension: {feed.get('dimension')}"
            logger.warning(warning)
            warnings = warnings + [warning]
            continue
        if content == "":
            warning = f"Extracted feed content is empty for dimension={dimension.value}"
            logger.warning(warning)
            warnings = warnings + [warning]
            continue

        recall_res = await recallFineGrainedFeeds(
            user_id=user_id,
            fr_id=fr_id,
            query=content,
            scope=[{"scope": dimension, "top_k": top_k}],
        )

        recalled_candidates = []
        if recall_res.get("status") == 200:
            recalled_items = []
            raw_items = recall_res.get("items", {})
            if isinstance(raw_items, dict):
                recalled_items = raw_items.get(dimension.value, [])

            for item in recalled_items:
                if not isinstance(item, dict):
                    continue
                raw_feed = item.get("fine_grained_feed")
                if not isinstance(raw_feed, dict):
                    continue

                recalled_dimension = parseEnum(
                    FineGrainedFeedDimension, raw_feed.get("dimension")
                )
                recalled_confidence = parseEnum(
                    FineGrainedFeedConfidence, raw_feed.get("confidence")
                )
                recalled_candidates.append(
                    {
                        "id": raw_feed.get("id"),
                        "dimension": recalled_dimension or dimension,
                        "sub_dimension": raw_feed.get("sub_dimension"),
                        "confidence": recalled_confidence or feed.get("confidence"),
                        "content": normalizeText(raw_feed.get("content")),
                        "score": float(item.get("score") or 0),
                    }
                )
        else:
            warning = (
                f"Recall failed for dimension={dimension.value}, "
                f"message={recall_res.get('message')}"
            )
            logger.warning(warning)
            warnings = warnings + [warning]

        handled_flag = False
        plan_item = {
            "extracted_feed": feed,
            "action": "add",
            "target_feed_id": None,
            "merged_content": None,
            "reason": "No relevant recalled feed, add new feed",
            "recalled_candidates": recalled_candidates,
        }

        for recalled_feed in recalled_candidates:
            old_content = normalizeText(recalled_feed.get("content"))
            if old_content == "":
                continue
            LLM_compare_res = await _compareFieldViaLLM(
                field_name=f"fine_grained_feed.{dimension.value}",
                field_type="string",
                old_value=old_content,
                new_value=content,
            )
            tag = normalizeText(LLM_compare_res.get("tag"))
            final_value = normalizeText(LLM_compare_res.get("final_value"))
            detail = normalizeText(LLM_compare_res.get("detail"))

            if tag == "irrelevant":
                continue
            if tag == "equivalent":
                handled_flag = True
                plan_item = {
                    "extracted_feed": feed,
                    "action": "skip",
                    "target_feed_id": recalled_feed.get("id"),
                    "merged_content": None,
                    "reason": detail or "Equivalent to recalled feed",
                    "recalled_candidates": recalled_candidates,
                }
                break
            if tag in {"supplementary", "new_adopted"}:
                handled_flag = True
                plan_item = {
                    "extracted_feed": feed,
                    "action": "update",
                    "target_feed_id": recalled_feed.get("id"),
                    "merged_content": final_value or content,
                    "reason": detail or f"{tag} by LLM compare",
                    "recalled_candidates": recalled_candidates,
                }
                break
            if tag == "conflictive":
                handled_flag = True
                plan_item = {
                    "extracted_feed": feed,
                    "action": "conflict",
                    "target_feed_id": recalled_feed.get("id"),
                    "merged_content": final_value or content,
                    "reason": detail or "Conflictive by LLM compare",
                    "recalled_candidates": recalled_candidates,
                }
                break

            warning = (
                f"Unexpected compare tag={tag}, "
                f"dimension={dimension.value}, target_feed_id={recalled_feed.get('id')}"
            )
            logger.warning(warning)
            warnings = warnings + [warning]

        if not handled_flag and len(recalled_candidates) > 0:
            plan_item["reason"] = "All recalled feeds are irrelevant"

        feed_upsert_plan.append(plan_item)

    action_counter = {"add": 0, "update": 0, "skip": 0, "conflict": 0}
    for item in feed_upsert_plan:
        action = item.get("action")
        if action in action_counter:
            action_counter[action] += 1

    logs += [
        {
            "step": "nodePlanFineGrainedFeedUpsert",
            "status": "ok",
            "detail": "FineGrainedFeed upsert plan generated",
            "data": {
                "top_k": top_k,
                "input_feed_count": len(extracted_feeds),
                "planned_feed_count": len(feed_upsert_plan),
                "action_counter": action_counter,
            },
        }
    ]
    logger.info(
        f"feed_upsert_plan: \n{json.dumps(feed_upsert_plan, ensure_ascii=False, indent=2, default=jsonDefault)}\n"
    )
    logger.info("nodePlanFineGrainedFeedUpsert executed finished\n")
    return {
        "feed_upsert_plan": feed_upsert_plan,
        "warnings": warnings,
        "logs": logs,
    }


async def nodePersistFineGrainedFeedUpsert(state: FRBuildingGraphState) -> dict:
    """
    FineGrainedFeed 更新落库
    """
    logger.info("nodePersistFineGrainedFeedUpsert is called")
    warnings = state.get("warnings") or []
    logs = state.get("logs") or []
    request = state.get("request") or {}
    original_source_id = state.get("original_source_id")
    feed_upsert_plan = state.get("feed_upsert_plan") or []

    user_id = request.get("user_id")
    fr_id = request.get("fr_id")
    if not isinstance(user_id, int) or not isinstance(fr_id, int):
        logger.error("Invalid request.user_id or request.fr_id")
        raise ValueError("Invalid request.user_id or request.fr_id")
    if not isinstance(original_source_id, int):
        logger.error("Invalid original_source_id")
        raise ValueError("Invalid original_source_id")

    if not isinstance(feed_upsert_plan, list) or len(feed_upsert_plan) == 0:
        logs += [
            {
                "step": "nodePersistFineGrainedFeedUpsert",
                "status": "skip",
                "detail": "No FineGrainedFeed upsert plan to persist",
                "data": {},
            }
        ]
        logger.info("nodePersistFineGrainedFeedUpsert executed finished\n")
        return {
            "feed_upsert_results": [],
            "warnings": warnings,
            "logs": logs,
        }

    feed_upsert_results = []

    for plan_item in feed_upsert_plan:
        if not isinstance(plan_item, dict):
            warning = f"Invalid plan item: {plan_item}"
            logger.warning(warning)
            warnings = warnings + [warning]
            continue

        extracted_feed = plan_item.get("extracted_feed") or {}
        action = normalizeText(plan_item.get("action"))
        target_feed_id = plan_item.get("target_feed_id")
        merged_content = normalizeText(plan_item.get("merged_content"))
        reason = normalizeText(plan_item.get("reason"))

        dimension = extracted_feed.get("dimension")
        sub_dimension = (
            normalizeText(extracted_feed.get("sub_dimension"))
            if extracted_feed.get("sub_dimension")
            else None
        )
        content = normalizeText(extracted_feed.get("content"))
        confidence = extracted_feed.get("confidence")

        if not isinstance(dimension, FineGrainedFeedDimension):
            warning = f"Invalid dimension in plan item: {dimension}"
            logger.warning(warning)
            warnings = warnings + [warning]
            continue
        if not isinstance(confidence, FineGrainedFeedConfidence):
            warning = (
                f"Invalid confidence in plan item for dimension={dimension.value}: "
                f"{confidence}"
            )
            logger.warning(warning)
            warnings = warnings + [warning]
            continue

        result_item = {
            "action": action,
            "dimension": dimension.value,
            "sub_dimension": sub_dimension,
            "target_feed_id": target_feed_id,
            "status": 200,
            "message": "ok",
            "reason": reason,
        }

        try:
            if action == "skip":
                result_item["message"] = "Skip equivalent feed"
            elif action == "add":
                if content == "":
                    result_item["status"] = -1
                    result_item["message"] = "Empty content for add action"
                else:
                    add_res = await addFineGrainedFeed(
                        user_id=user_id,
                        fr_id=fr_id,
                        original_source_id=original_source_id,
                        dimension=dimension,
                        confidence=confidence,
                        content=content,
                        sub_dimension=sub_dimension,
                    )
                    result_item["status"] = add_res.get("status", -1)
                    result_item["message"] = add_res.get(
                        "message", "Add FineGrainedFeed failed"
                    )
            elif action == "update":
                if not isinstance(target_feed_id, int):
                    result_item["status"] = -1
                    result_item["message"] = "target_feed_id is required for update"
                elif merged_content == "":
                    result_item["status"] = -2
                    result_item["message"] = "merged_content is required for update"
                else:
                    update_res = await updateFineGrainedFeed(
                        user_id=user_id,
                        fr_id=fr_id,
                        fine_grained_feed_id=target_feed_id,
                        new_original_source_id=original_source_id,
                        new_content=merged_content,
                        new_sub_dimension=sub_dimension,
                    )
                    result_item["status"] = update_res.get("status", -1)
                    result_item["message"] = update_res.get(
                        "message", "Update FineGrainedFeed failed"
                    )
            elif action == "conflict":
                if not isinstance(target_feed_id, int):
                    result_item["status"] = -1
                    result_item["message"] = "target_feed_id is required for conflict"
                elif merged_content == "":
                    result_item["status"] = -2
                    result_item["message"] = "merged_content is required for conflict"
                else:
                    recalled_candidates = plan_item.get("recalled_candidates")
                    old_value = ""
                    if isinstance(recalled_candidates, list):
                        for candidate in recalled_candidates:
                            if not isinstance(candidate, dict):
                                continue
                            if candidate.get("id") != target_feed_id:
                                continue
                            old_value = normalizeText(candidate.get("content"))
                            break
                    if old_value == "":
                        old_value = merged_content

                    # 降级方案：先记录冲突，再直接采用新内容进行更新
                    conflict_res = addFineGrainedFeedConflict(
                        user_id=user_id,
                        fr_id=fr_id,
                        dimension=dimension,
                        feed_ids=[target_feed_id],
                        old_value=old_value,
                        new_value=content or merged_content,
                        conflict_detail=reason or "Conflictive by LLM compare",
                        status=ConflictStatus.PENDING,
                    )

                    update_res = await updateFineGrainedFeed(
                        user_id=user_id,
                        fr_id=fr_id,
                        fine_grained_feed_id=target_feed_id,
                        new_original_source_id=original_source_id,
                        new_content=merged_content,
                        new_sub_dimension=sub_dimension,
                    )
                    result_item["status"] = (
                        200
                        if conflict_res.get("status") == 200
                        and update_res.get("status") == 200
                        else -3
                    )
                    result_item["message"] = (
                        "Conflict recorded and feed updated"
                        if result_item["status"] == 200
                        else (
                            f"Conflict/update failed: "
                            f"conflict={conflict_res.get('message')}, "
                            f"update={update_res.get('message')}"
                        )
                    )
            else:
                result_item["status"] = -9
                result_item["message"] = f"Unsupported action: {action}"
        except Exception as e:
            logger.error(f"Persist feed upsert failed: {str(e)}")
            result_item["status"] = -99
            result_item["message"] = f"Exception: {str(e)}"

        if result_item.get("status") != 200:
            warning = (
                f"Persist failed, action={action}, dimension={dimension.value}, "
                f"message={result_item.get('message')}"
            )
            logger.warning(warning)
            warnings = warnings + [warning]

        feed_upsert_results.append(result_item)

    success_count = len(
        [item for item in feed_upsert_results if item.get("status") == 200]
    )
    logs += [
        {
            "step": "nodePersistFineGrainedFeedUpsert",
            "status": "ok",
            "detail": "FineGrainedFeed upsert persisted",
            "data": {
                "plan_count": len(feed_upsert_plan),
                "result_count": len(feed_upsert_results),
                "success_count": success_count,
                "failed_count": len(feed_upsert_results) - success_count,
            },
        }
    ]

    logger.info("nodePersistFineGrainedFeedUpsert executed finished\n")
    return {
        "feed_upsert_results": feed_upsert_results,
        "warnings": warnings,
        "logs": logs,
    }


def nodeBuildFRBuildingGraphOutput(
    state: FRBuildingGraphState,
) -> FRBuildingGraphOutput:
    """
    汇总 graph 执行结果，构建 FRBuildingGraphOutput
    """
    logger.info("nodeBuildFRBuildingGraphOutput is called")
    warnings = state.get("warnings") or []
    errors = state.get("errors") or []
    logs = state.get("logs") or []

    original_source_id = state.get("original_source_id")
    fr_update_result = state.get("fr_update_result") or {}
    feed_upsert_results = state.get("feed_upsert_results") or []

    has_error = len(errors) > 0
    has_failed_feed = any(item.get("status") != 200 for item in feed_upsert_results)
    fr_update_failed = isinstance(fr_update_result, dict) and (
        fr_update_result.get("status") not in (None, 200)
    )

    if has_error or fr_update_failed or has_failed_feed:
        status = 500
        message = "FR building completed with partial failure"
    else:
        status = 200
        message = "FR building completed"

    logs += [
        {
            "step": "nodeBuildFRBuildingGraphOutput",
            "status": "ok",
            "detail": "FRBuildingGraph output built",
            "data": {
                "status": status,
                "has_error": has_error,
                "fr_update_failed": fr_update_failed,
                "has_failed_feed": has_failed_feed,
                "warning_count": len(warnings),
                "error_count": len(errors),
            },
        }
    ]

    logger.info("nodeBuildFRBuildingGraphOutput executed finished\n")
    return {
        "status": status,
        "message": message,
        "original_source_id": original_source_id,
        "fr_update_result": fr_update_result,
        "feed_upsert_results": feed_upsert_results,
        "logs": logs,
        "warnings": warnings,
        "errors": errors,
    }


async def nodeGenerateFRBuildingReport(
    state: FRBuildingGraphState,
) -> dict:
    """
    生成 FR 构建报告
    """
    logger.info("nodeGenerateFRBuildingReport is called")
    request = state.get("request") or {}
    user_id = request.get("user_id")
    fr_id = request.get("fr_id")
    if not isinstance(user_id, int):
        logger.error("Invalid request.user_id")
        raise ValueError("Invalid request.user_id")
    if not isinstance(fr_id, int):
        logger.error("Invalid request.fr_id")
        raise ValueError("Invalid request.fr_id")

    warnings = state.get("warnings") or []
    logs = state.get("logs") or []
    output = {
        "status": state.get("status"),
        "message": state.get("message"),
        "original_source_id": state.get("original_source_id"),
        "fr_update_result": state.get("fr_update_result"),
        "feed_upsert_results": state.get("feed_upsert_results"),
        "logs": state.get("logs"),
        "warnings": state.get("warnings"),
        "errors": state.get("errors"),
    }
    llm = prepareLLM(
        "DOUBAO_2_0_LITE",
        options={
            "temperature": 0,
            "reasoning_effort": "low",
        },
    )
    report_markdown = ""
    try:
        FR_BUILDING_REPORT = await getPrompt(os.getenv("FR_BUILDING_REPORT"))
        if not FR_BUILDING_REPORT:
            logger.error("FR_BUILDING_REPORT prompt not found")
            raise ValueError("FR_BUILDING_REPORT prompt not found")

        user_prompt = json.dumps(
            output, ensure_ascii=False, indent=2, default=jsonDefault
        )
        response = await llm.ainvoke(
            [
                SystemMessage(content=FR_BUILDING_REPORT),
                HumanMessage(content=user_prompt),
            ]
        )
        report_markdown = normalizeText(response.content)
    except Exception as e:
        warning = f"Generate FR report via LLM failed: {str(e)}"
        logger.warning(warning)
        warnings = warnings + [warning]
        raise ValueError(warning)

    persist_res = addFRBuildingGraphReport(
        user_id=user_id,
        fr_id=fr_id,
        report=report_markdown,
    )
    if persist_res.get("status") != 200:
        logger.error(
            f"Persist FRBuildingGraphReport failed: {persist_res.get('message', '')}"
        )
        raise ValueError(
            f"Persist FRBuildingGraphReport failed: {persist_res.get('message', '')}"
        )

    report_id = persist_res.get("fr_building_graph_report_id")
    logs += [
        {
            "step": "nodeGenerateFRBuildingReport",
            "status": "ok",
            "detail": "FR building report generated and persisted",
            "data": {
                "fr_building_graph_report_id": report_id,
                "report_length": len(report_markdown),
            },
        }
    ]
    logger.info(f"report_markdown: \n{report_markdown}\n")

    logger.info("nodeGenerateFRBuildingReport executed finished\n")
    return {
        "fr_building_report": report_markdown,
        "warnings": warnings,
        "logs": logs,
    }
