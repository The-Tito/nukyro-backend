"""Rutas de las evaluaciones. Sin lógica: validan, llaman al servicio y renuevan la cookie."""

from fastapi import APIRouter, Request, Response

from nukyro.auth import authenticate, refresh_cookie
from nukyro.modules.assessment import service
from nukyro.modules.assessment.schemas import AnswerIn, AssessmentOut, ProgressOut

router = APIRouter(prefix="/api/v1")


def engine(request: Request):
    return request.app.state.engines["api"]


@router.get("/sessions/{session_id}/assessments/{kind}", response_model=AssessmentOut)
def get_assessment(session_id: str, kind: str, request: Request, response: Response):
    auth = authenticate(request)
    result = service.get_assessment(engine(request), auth, session_id, kind)
    refresh_cookie(response, auth)
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
    auth = authenticate(request)
    result = service.put_answer(engine(request), auth, session_id, kind, question_key, body)
    refresh_cookie(response, auth)
    return result


@router.post("/sessions/{session_id}/assessments/{kind}/submit", response_model=AssessmentOut)
def submit(session_id: str, kind: str, request: Request, response: Response):
    auth = authenticate(request)
    result = service.submit(engine(request), auth, session_id, kind)
    refresh_cookie(response, auth)
    return result
