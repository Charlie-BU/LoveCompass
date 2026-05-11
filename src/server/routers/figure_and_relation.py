import logging
from robyn import Request, Response, SubRouter
from robyn.authentication import BearerGetter

from src.database.enums import FigureRole, Gender, MBTI, parseEnum
from src.server.auth import AuthHandler
from src.services.figure_and_relation import (
    addFigureAndRelation,
    addFRBuildingGraphReport,
    deleteFigureAndRelation,
    deleteFRBuildingGraphReport,
    getAllFigureAndRelations,
    getAllFRBuildingGraphReport,
    getFigureAndRelation,
    getFRAllContext,
    getFRBuildingGraphReport,
    ifFRBelongsToUser,
    syncAllFeedsToFRCore,
    syncFeedsToFRCore,
    updateFigureAndRelation,
)
from src.services.user import getUserIdByAccessToken
from src.utils.index import parseInt

logger = logging.getLogger(__name__)
figure_and_relation_router = SubRouter(__file__, prefix="/fr")


@figure_and_relation_router.exception
def handleException(error):
    logger.error(error)
    return Response(status_code=500, description="Internal Server Error", headers={})


figure_and_relation_router.configure_authentication(
    AuthHandler(token_getter=BearerGetter())
)


@figure_and_relation_router.post("/addFigureAndRelation", auth_required=True)
async def addFigureAndRelationRouter(request: Request):
    body = request.json()
    figure_name = body.get("figure_name", "")
    figure_gender = parseEnum(Gender, body.get("figure_gender", None))
    figure_role = parseEnum(FigureRole, body.get("figure_role", None))
    figure_mbti_raw = body.get("figure_mbti", None)
    figure_mbti = parseEnum(MBTI, figure_mbti_raw)
    if figure_mbti_raw in ("", None):
        figure_mbti = None

    if not isinstance(figure_name, str) or figure_gender is None or figure_role is None:
        return {"status": -1, "message": "Add FigureAndRelation args are invalid"}
    if figure_mbti_raw not in ("", None) and figure_mbti is None:
        return {"status": -1, "message": "Invalid figure_mbti"}

    user_id = getUserIdByAccessToken(request=request)
    return addFigureAndRelation(
        user_id=user_id,
        figure_name=figure_name,
        figure_gender=figure_gender,
        figure_role=figure_role,
        figure_mbti=figure_mbti,
        figure_birthday=body.get("figure_birthday", None),
        figure_occupation=body.get("figure_occupation", None),
        figure_education=body.get("figure_education", None),
        figure_residence=body.get("figure_residence", None),
        figure_hometown=body.get("figure_hometown", None),
        exact_relation=body.get("exact_relation", ""),
    )


@figure_and_relation_router.post("/deleteFigureAndRelation", auth_required=True)
async def deleteFigureAndRelationRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return deleteFigureAndRelation(user_id=user_id, fr_id=fr_id)


@figure_and_relation_router.post("/updateFigureAndRelation", auth_required=True)
async def updateFigureAndRelationRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    fr_body = body.get("fr_body", None)
    original_source_id_raw = body.get("original_source_id", None)
    original_source_id = (
        parseInt(original_source_id_raw)
        if original_source_id_raw is not None
        else original_source_id_raw
    )

    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    if not isinstance(fr_body, dict):
        return {"status": -1, "message": "fr_body is invalid"}
    if original_source_id_raw is not None and original_source_id is None:
        return {"status": -1, "message": "original_source_id is invalid"}

    if "figure_gender" in fr_body:
        parsed_gender = parseEnum(Gender, fr_body.get("figure_gender", None))
        if parsed_gender is None:
            return {"status": -1, "message": "Invalid figure_gender"}
        fr_body["figure_gender"] = parsed_gender
    if "figure_role" in fr_body:
        parsed_role = parseEnum(FigureRole, fr_body.get("figure_role", None))
        if parsed_role is None:
            return {"status": -1, "message": "Invalid figure_role"}
        fr_body["figure_role"] = parsed_role
    if "figure_mbti" in fr_body:
        mbti_raw = fr_body.get("figure_mbti", None)
        parsed_mbti = parseEnum(MBTI, mbti_raw)
        if mbti_raw not in ("", None) and parsed_mbti is None:
            return {"status": -1, "message": "Invalid figure_mbti"}
        fr_body["figure_mbti"] = parsed_mbti

    user_id = getUserIdByAccessToken(request=request)
    return updateFigureAndRelation(
        user_id=user_id,
        fr_id=fr_id,
        fr_body=fr_body,
        original_source_id=original_source_id,
    )


@figure_and_relation_router.get("/getFigureAndRelation", auth_required=True)
async def getFigureAndRelationRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return getFigureAndRelation(user_id=user_id, fr_id=fr_id)


@figure_and_relation_router.get("/getAllFigureAndRelations", auth_required=True)
async def getAllFigureAndRelationsRouter(request: Request):
    user_id = getUserIdByAccessToken(request=request)
    return getAllFigureAndRelations(user_id=user_id)


@figure_and_relation_router.post("/addFRBuildingGraphReport", auth_required=True)
async def addFRBuildingGraphReportRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    report = body.get("report", "")
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    if not isinstance(report, str):
        return {"status": -1, "message": "report is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return addFRBuildingGraphReport(user_id=user_id, fr_id=fr_id, report=report)


@figure_and_relation_router.post("/deleteFRBuildingGraphReport", auth_required=True)
async def deleteFRBuildingGraphReportRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    report_id = parseInt(body.get("fr_building_graph_report_id", None))
    if fr_id is None or report_id is None:
        return {
            "status": -1,
            "message": "fr_id or fr_building_graph_report_id is invalid",
        }
    user_id = getUserIdByAccessToken(request=request)
    return deleteFRBuildingGraphReport(
        user_id=user_id,
        fr_id=fr_id,
        fr_building_graph_report_id=report_id,
    )


@figure_and_relation_router.get("/getFRBuildingGraphReport", auth_required=True)
async def getFRBuildingGraphReportRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    report_id = parseInt(request.query_params.get("fr_building_graph_report_id", None))
    if fr_id is None or report_id is None:
        return {
            "status": -1,
            "message": "fr_id or fr_building_graph_report_id is invalid",
        }
    user_id = getUserIdByAccessToken(request=request)
    return getFRBuildingGraphReport(
        user_id=user_id,
        fr_id=fr_id,
        fr_building_graph_report_id=report_id,
    )


@figure_and_relation_router.get("/getAllFRBuildingGraphReport", auth_required=True)
async def getAllFRBuildingGraphReportRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return getAllFRBuildingGraphReport(user_id=user_id, fr_id=fr_id)


@figure_and_relation_router.get("/getFRAllContext", auth_required=True)
async def getFRAllContextRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    query = request.query_params.get("query", None)
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return await getFRAllContext(user_id=user_id, fr_id=fr_id, query=query)


@figure_and_relation_router.post("/syncFeedsToFRCore", auth_required=True)
async def syncFeedsToFRCoreRouter(request: Request):
    body = request.json()
    fr_id = parseInt(body.get("fr_id", None))
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return await syncFeedsToFRCore(user_id=user_id, fr_id=fr_id)


@figure_and_relation_router.post("/syncAllFeedsToFRCore", auth_required=True)
async def syncAllFeedsToFRCoreRouter(request: Request):
    user_id = getUserIdByAccessToken(request=request)
    return await syncAllFeedsToFRCore(user_id=user_id)


# @figure_and_relation_router.get("/getFROverallUpdateLogsThisRound", auth_required=True)
# async def getFROverallUpdateLogsThisRoundRouter(request: Request):
#     fr_id = parseInt(request.query_params.get("fr_id", None))
#     original_source_id = parseInt(request.query_params.get("original_source_id", None))
#     if fr_id is None or original_source_id is None:
#         return {"status": -1, "message": "fr_id or original_source_id is invalid"}
#     return {
#         "status": 200,
#         "message": "Success",
#         "logs": getFROverallUpdateLogsThisRound(
#             fr_id=fr_id, original_source_id=original_source_id
#         ),
#     }


@figure_and_relation_router.get("/ifFRBelongsToUser", auth_required=True)
async def ifFRBelongsToUserRouter(request: Request):
    fr_id = parseInt(request.query_params.get("fr_id", None))
    if fr_id is None:
        return {"status": -1, "message": "fr_id is invalid"}
    user_id = getUserIdByAccessToken(request=request)
    return ifFRBelongsToUser(user_id=user_id, fr_id=fr_id)
