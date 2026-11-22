"""Rutas de la simulación. Sin lógica: validan, llaman al servicio y renuevan la cookie."""

from fastapi import APIRouter, Request, Response

from nukyro.modules.simulation import service
from nukyro.modules.simulation.schemas import (
    AdvanceIn,
    DecisionIn,
    DecisionOut,
    SessionDetailOut,
)
from nukyro.security import require_secret, set_cookie

router = APIRouter(prefix="/api/v1")


def engine(request: Request):
    return request.app.state.engines["api"]


@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
def get_session(session_id: str, request: Request, response: Response):
    secret = require_secret(request)
    result = service.get_session(engine(request), secret, session_id)
    set_cookie(response, secret)
    return result


@router.post("/sessions/{session_id}/decisions", response_model=DecisionOut)
def decide(session_id: str, body: DecisionIn, request: Request, response: Response):
    secret = require_secret(request)
    result = service.decide(engine(request), secret, session_id, body)
    set_cookie(response, secret)
    return result


@router.post("/sessions/{session_id}/advance", response_model=SessionDetailOut)
def advance(session_id: str, body: AdvanceIn, request: Request, response: Response):
    secret = require_secret(request)
    result = service.advance(engine(request), secret, session_id, body)
    set_cookie(response, secret)
    return result
