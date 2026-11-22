"""Rutas de las evaluaciones. Sin lógica: validan, llaman al servicio y renuevan la cookie."""

from fastapi import APIRouter, Request, Response

from nukyro.modules.assessment import service
from nukyro.modules.assessment.schemas import AnswerIn, AssessmentOut, ProgressOut
from nukyro.security import require_secret, set_cookie

router = APIRouter(prefix="/api/v1")


def engine(request: Request):
    return request.app.state.engines["api"]


@router.get("/sessions/{session_id}/assessments/{kind}", response_model=AssessmentOut)
def get_assessment(session_id: str, kind: str, request: Request, response: Response):
    secret = require_secret(request)
    result = service.get_assessment(engine(request), secret, session_id, kind)
    set_cookie(response, secret)
    return result


@router.put(
    "/sessions/{session_id}/assessments/{kind}/answers/{question_key}", response_model=ProgressOut
)
def put_answer(
    session_id: str,
    kind: str,
    question_key: str,
    body: AnswerIn,
    request: Request,
    response: Response,
):
    secret = require_secret(request)
    result = service.put_answer(engine(request), secret, session_id, kind, question_key, body)
    set_cookie(response, secret)
    return result


@router.post("/sessions/{session_id}/assessments/{kind}/submit", response_model=AssessmentOut)
def submit(session_id: str, kind: str, request: Request, response: Response):
    secret = require_secret(request)
    result = service.submit(engine(request), secret, session_id, kind)
    set_cookie(response, secret)
    return result
