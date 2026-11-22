"""Seguridad compartida: cookie anónima del participante, CSRF y caché (ADR-008, RF-062)."""

import hashlib
import logging
import secrets

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

COOKIE = "__Host-nukyro_participant"
MAX_AGE = 30 * 24 * 3600  # 30 días, renovada al usarse
SAFE_METHODS = {"GET", "HEAD"}


def new_secret() -> str:
    return secrets.token_urlsafe(32)  # 256 bits


def hash_secret(secret: str) -> bytes:
    return hashlib.sha256(secret.encode()).digest()  # en la base solo va el hash


def set_cookie(response: Response, secret: str) -> None:
    # El prefijo __Host- exige Secure, Path=/ y ningún Domain
    response.set_cookie(
        COOKIE, secret, max_age=MAX_AGE, path="/", secure=True, httponly=True, samesite="lax"
    )


def cookie_secret(request: Request) -> str | None:
    value = request.cookies.get(COOKIE)
    return value if value and len(value) <= 128 else None


def require_secret(request: Request) -> str:
    secret = cookie_secret(request)
    if secret is None:
        raise HTTPException(401)
    return secret


def install(app: FastAPI) -> None:
    """CSRF en toda ruta que no sea GET/HEAD y Cache-Control: no-store en toda la API."""

    @app.middleware("http")
    async def csrf_and_cache(request: Request, call_next):
        if request.method not in SAFE_METHODS and not (
            request.headers.get("origin") == request.app.state.origin
            and request.headers.get("x-nukyro-request") == "1"
        ):
            body = {"error": {"code": "forbidden", "message": "Solicitud no permitida"}}
            response = JSONResponse(body, status_code=403)
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                # Se atiende aquí para que ninguna traza (con parámetros SQL) llegue a los logs
                logging.getLogger("nukyro").error("Error no controlado: %s", type(exc).__name__)
                body = {"error": {"code": "internal_error", "message": "Error interno"}}
                response = JSONResponse(body, status_code=500)
        response.headers["Cache-Control"] = "no-store"
        return response
