"""Rutas del recorrido de entrada. Sin lógica: validan, llaman al servicio y fijan la cookie."""

from fastapi import APIRouter, Request, Response

from nukyro.auth import authenticate, refresh_cookie
from nukyro.modules.entry import service
from nukyro.modules.entry.schemas import (
    AcceptanceIn,
    ParticipantOut,
    SessionIn,
    SessionOut,
    SessionsOut,
)
from nukyro.security import set_cookie

router = APIRouter(prefix="/api/v1")


def engine(request: Request):
    return request.app.state.engines["api"]


@router.get("/entry")
def entry(request: Request):
    return service.entry(engine(request), request.app.state.documents)


@router.post("/participants", response_model=ParticipantOut)
def create_participant(body: AcceptanceIn, request: Request, response: Response):
    state, secret = service.create_participant(
        engine(request), request.app.state.documents, body, authenticate(request, required=False)
    )
    response.status_code = 201 if state == "created" else 200
    if secret is not None:  # con cuenta no hay cookie que entregar
        set_cookie(response, secret)
    return {"status": state}


@router.post("/sessions", response_model=SessionOut, status_code=201)
def start_session(body: SessionIn, request: Request, response: Response):
    auth = authenticate(request)
    result = service.start_session(engine(request), request.app.state.documents, auth, body)
    refresh_cookie(response, auth)
    return result


@router.get("/sessions", response_model=SessionsOut)
def list_sessions(request: Request, response: Response):
    auth = authenticate(request)
    result = service.list_sessions(engine(request), auth)
    refresh_cookie(response, auth)
    return result
