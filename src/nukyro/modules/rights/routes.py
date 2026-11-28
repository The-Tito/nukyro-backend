"""Derechos del participante a través de sus propias credenciales (RF-078, RF-079)."""

from fastapi import APIRouter, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from nukyro.auth import authenticate, clear_cookie
from nukyro.modules.rights import service

router = APIRouter(prefix="/api/v1/participants/me")


@router.get("/data")
def export_anonymous_data(request: Request):
    auth = authenticate(request)
    result = service.export_anonymous_data(request.app.state.engines["api"], auth)
    return JSONResponse(
        jsonable_encoder(result),
        headers={"Content-Disposition": 'attachment; filename="nukyro-data.json"'},
    )


@router.delete("/data", status_code=204)
def erase_anonymous_data(request: Request):
    auth = authenticate(request)
    service.erase_anonymous_data(request.app.state.engines["api"], auth)
    response = Response(status_code=204)
    clear_cookie(response)
    return response


@router.put("/statistics-opposition", status_code=204)
def oppose_statistics(request: Request):
    auth = authenticate(request)
    service.oppose_statistics(request.app.state.engines["api"], auth)
    return Response(status_code=204)
