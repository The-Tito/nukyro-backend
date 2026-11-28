"""Rutas de la encuesta. Sin lógica: validan, llaman al servicio y renuevan la cookie."""

from fastapi import APIRouter, Request, Response

from nukyro.auth import authenticate, refresh_cookie
from nukyro.modules.survey import service
from nukyro.modules.survey.schemas import SubmittedOut, SurveyIn, SurveyOut

router = APIRouter(prefix="/api/v1")


def engine(request: Request):
    return request.app.state.engines["api"]


@router.get(
    "/sessions/{session_id}/survey", response_model=SurveyOut, response_model_exclude_none=True
)
def get_survey(session_id: str, request: Request, response: Response):
    auth = authenticate(request)
    result = service.get_survey(engine(request), auth, session_id)
    refresh_cookie(response, auth)
    return result


@router.post("/sessions/{session_id}/survey", response_model=SubmittedOut, status_code=201)
def post_survey(session_id: str, body: SurveyIn, request: Request, response: Response):
    auth = authenticate(request)
    result = service.submit_survey(engine(request), auth, session_id, body)
    refresh_cookie(response, auth)
    return result
