"""Ruta del resumen. Sin lógica: valida, llama al servicio y renueva la cookie."""

from fastapi import APIRouter, Request, Response

from nukyro.auth import authenticate, refresh_cookie
from nukyro.modules.summary import service
from nukyro.modules.summary.schemas import SummaryOut

router = APIRouter(prefix="/api/v1")


@router.get("/sessions/{session_id}/summary", response_model=SummaryOut)
def get_summary(session_id: str, request: Request, response: Response):
    auth = authenticate(request)
    result = service.get_summary(request.app.state.engines["api"], auth, session_id)
    refresh_cookie(response, auth)
    return result
