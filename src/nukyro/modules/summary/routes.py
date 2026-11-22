"""Ruta del resumen. Sin lógica: valida, llama al servicio y renueva la cookie."""

from fastapi import APIRouter, Request, Response

from nukyro.modules.summary import service
from nukyro.modules.summary.schemas import SummaryOut
from nukyro.security import require_secret, set_cookie

router = APIRouter(prefix="/api/v1")


@router.get("/sessions/{session_id}/summary", response_model=SummaryOut)
def get_summary(session_id: str, request: Request, response: Response):
    secret = require_secret(request)
    result = service.get_summary(request.app.state.engines["api"], secret, session_id)
    set_cookie(response, secret)
    return result
