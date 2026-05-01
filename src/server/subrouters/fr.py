from robyn import SubRouter, Request, Response
from robyn.authentication import BearerGetter
import logging

from src.server.authentication import AuthHandler
from src.services.user import getUserIdByAccessToken
from src.services.figure_and_relation import (
    addFigureAndRelation,
    deleteFigureAndRelation,
    updateFigureAndRelation,
    getFigureAndRelation,
    getAllFigureAndRelations,
    frBelongsToUser,
    getFRAccessContextByOpenId,
    addFRBuildingGraphReport,
    deleteFRBuildingGraphReport,
    getFRBuildingGraphReport,
    getAllFRBuildingGraphReport,
    getFRAllContext,
    syncFeedsToFRCore,
    syncAllFeedsToFRCore,
    getFROverallUpdateLogsThisRound,
)
from src.database.enums import Gender, FigureRole, MBTI, parseEnum
from src.utils.index import toInt


logger = logging.getLogger(__name__)
fr_router = SubRouter(__file__, prefix="/fr")


@fr_router.exception
def handleException(error):
    logger.error(error)
    return Response(status_code=500, description="Internal Server Error", headers={})


fr_router.configure_authentication(AuthHandler(token_getter=BearerGetter()))


def _normalizeFigureAndRelationBody(fr_body) -> dict:
    """
    将 body 中的 FR 相关字段转化为枚举
    """
    if not isinstance(fr_body, dict):
        return {}
    data = dict(fr_body)
    if "figure_gender" in data:
        data["figure_gender"] = parseEnum(Gender, data.get("figure_gender"))
    if "figure_role" in data:
        data["figure_role"] = parseEnum(FigureRole, data.get("figure_role"))
    if "figure_mbti" in data:
        data["figure_mbti"] = parseEnum(MBTI, data.get("figure_mbti"))
    return data


@fr_router.post("/addFigureAndRelation", auth_required=True)
async def addFigureAndRelationRouter(request: Request):
    """
    添加 FigureAndRelation
    """
    id = getUserIdByAccessToken(request)
    body = request.json()
    return addFigureAndRelation(
        user_id=id,
        figure_name=body.get("figure_name", ""),
        figure_gender=parseEnum(Gender, body.get("figure_gender")),  # type: ignore
        figure_role=parseEnum(FigureRole, body.get("figure_role")),  # type: ignore
        figure_mbti=parseEnum(MBTI, body.get("figure_mbti")),  # type: ignore
        figure_birthday=body.get("figure_birthday"),
        figure_occupation=body.get("figure_occupation"),
        figure_education=body.get("figure_education"),
        figure_residence=body.get("figure_residence"),
        figure_hometown=body.get("figure_hometown"),
        exact_relation=body.get("exact_relation", ""),
    )


@fr_router.post("/deleteFigureAndRelation", auth_required=True)
async def deleteFigureAndRelationRouter(request: Request):
    """
    通过 fr_id 软删除 FigureAndRelation
    """
    id = getUserIdByAccessToken(request)
    body = request.json()
    fr_id = toInt(body.get("fr_id"))
    return deleteFigureAndRelation(user_id=id, fr_id=fr_id)  # type: ignore


@fr_router.post("/updateFigureAndRelation", auth_required=True)
async def updateFigureAndRelationRouter(request: Request):
    """
    通过 fr_id 更新 FigureAndRelation
    """
    id = getUserIdByAccessToken(request)
    body = request.json()
    fr_id = toInt(body.get("fr_id"))
    original_source_id = toInt(body.get("original_source_id"))
    fr_body = _normalizeFigureAndRelationBody(body.get("fr_body"))
    return updateFigureAndRelation(
        user_id=id,
        fr_id=fr_id,  # type: ignore
        fr_body=fr_body,
        original_source_id=original_source_id,
    )


@fr_router.get("/getFigureAndRelation", auth_required=True)
async def getFigureAndRelationRouter(request: Request):
    """
    通过 fr_id 获取 FigureAndRelation
    """
    id = getUserIdByAccessToken(request)
    fr_id = toInt(request.query_params.get("fr_id", None))
    return getFigureAndRelation(user_id=id, fr_id=fr_id)  # type: ignore


@fr_router.get("/getAllFigureAndRelations", auth_required=True)
async def getAllFigureAndRelationsRouter(request: Request):
    """
    获取用户所有 FigureAndRelation（简要信息）
    """
    id = getUserIdByAccessToken(request)
    return getAllFigureAndRelations(user_id=id)


@fr_router.get("/frBelongsToUser", auth_required=True)
async def frBelongsToUserRouter(request: Request):
    """
    判断 fr 是否属于当前用户
    """
    id = getUserIdByAccessToken(request)
    fr_id = toInt(request.query_params.get("fr_id", None))
    return frBelongsToUser(user_id=id, fr_id=fr_id)  # type: ignore


@fr_router.get("/getFRAccessContextByOpenId")
async def getFRAccessContextByOpenIdRouter(request: Request):
    """
    基于飞书 open_id 获取 FR 访问上下文
    """
    open_id = request.query_params.get("open_id", None)
    fr_id = toInt(request.query_params.get("fr_id", None))
    return getFRAccessContextByOpenId(open_id=open_id, fr_id=fr_id)  # type: ignore


@fr_router.post("/addFRBuildingGraphReport", auth_required=True)
async def addFRBuildingGraphReportRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    fr_id = toInt(body.get("fr_id"))
    return addFRBuildingGraphReport(
        user_id=id,
        fr_id=fr_id,  # type: ignore
        report=body.get("report", ""),
    )


@fr_router.post("/deleteFRBuildingGraphReport", auth_required=True)
async def deleteFRBuildingGraphReportRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    fr_id = toInt(body.get("fr_id"))
    fr_building_graph_report_id = toInt(body.get("fr_building_graph_report_id"))
    return deleteFRBuildingGraphReport(
        user_id=id,
        fr_id=fr_id,  # type: ignore
        fr_building_graph_report_id=fr_building_graph_report_id,  # type: ignore
    )


@fr_router.get("/getFRBuildingGraphReport", auth_required=True)
async def getFRBuildingGraphReportRouter(request: Request):
    id = getUserIdByAccessToken(request)
    fr_id = toInt(request.query_params.get("fr_id", None))
    fr_building_graph_report_id = toInt(
        request.query_params.get("fr_building_graph_report_id", None)
    )
    return getFRBuildingGraphReport(
        user_id=id,
        fr_id=fr_id,  # type: ignore
        fr_building_graph_report_id=fr_building_graph_report_id,  # type: ignore
    )


@fr_router.get("/getAllFRBuildingGraphReport", auth_required=True)
async def getAllFRBuildingGraphReportRouter(request: Request):
    id = getUserIdByAccessToken(request)
    fr_id = toInt(request.query_params.get("fr_id", None))
    return getAllFRBuildingGraphReport(user_id=id, fr_id=fr_id)  # type: ignore


@fr_router.get("/getFRAllContext", auth_required=True)
async def getFRAllContextRouter(request: Request):
    id = getUserIdByAccessToken(request)
    fr_id = toInt(request.query_params.get("fr_id", None))
    query = request.query_params.get("query", None)
    return await getFRAllContext(
        user_id=id,
        fr_id=fr_id,  # type: ignore
        query=query if isinstance(query, str) else None,
    )


@fr_router.post("/syncFeedsToFRCore", auth_required=True)
async def syncFeedsToFRCoreRouter(request: Request):
    id = getUserIdByAccessToken(request)
    body = request.json()
    fr_id = toInt(body.get("fr_id"))
    return await syncFeedsToFRCore(user_id=id, fr_id=fr_id)  # type: ignore


@fr_router.post("/syncAllFeedsToFRCore", auth_required=True)
async def syncAllFeedsToFRCoreRouter(request: Request):
    id = getUserIdByAccessToken(request)
    return await syncAllFeedsToFRCore(user_id=id)


@fr_router.get("/getFROverallUpdateLogsThisRound", auth_required=True)
async def getFROverallUpdateLogsThisRoundRouter(request: Request):
    fr_id = toInt(request.query_params.get("fr_id", None))
    original_source_id = toInt(request.query_params.get("original_source_id", None))
    logs = getFROverallUpdateLogsThisRound(
        fr_id=fr_id,  # type: ignore
        original_source_id=original_source_id,  # type: ignore
    )
    return {
        "status": 200,
        "message": "Get FR overall update logs success",
        "items": logs,
    }
