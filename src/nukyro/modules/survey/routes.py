"""Rutas de la encuesta. Sin lógica: validan, llaman al servicio y renuevan la cookie."""

from fastapi import APIRouter, Request, Response

from nukyro.modules.survey import service
from nukyro.modules.survey.schemas import SubmittedOut, SurveyIn, SurveyOut
from nukyro.security import require_secret, set_cookie

router = APIRouter(prefix="/api/v1")


def engine(request: Request):
    return request.app.state.engines["api"]


@router.get(
    "/sessions/{session_id}/survey", response_model=SurveyOut, response_model_exclude_none=True
)
def get_survey(session_id: str, request: Request, response: Response):
    secret = require_secret(request)
    result = service.get_survey(engine(request), secret, session_id)
    set_cookie(response, secret)
    return result


@router.post("/sessions/{session_id}/survey", response_model=SubmittedOut, status_code=201)
def post_survey(session_id: str, body: SurveyIn, request: Request, response: Response):
    secret = require_secret(request)
    result = service.submit_survey(engine(request), secret, session_id, body)
    set_cookie(response, secret)
    return result
