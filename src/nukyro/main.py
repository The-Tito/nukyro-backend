"""Punto de entrada de la API: create_app, errores JSON y logs sin datos del cliente."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from nukyro import security
from nukyro.config import load_settings, load_web_settings
from nukyro.db import build_engines, verify_engines
from nukyro.modules.assessment.routes import router as assessment_router
from nukyro.modules.entry import service as entry_service
from nukyro.modules.entry.routes import router as entry_router
from nukyro.modules.simulation.routes import router as simulation_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("nukyro")


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    engines = build_engines(settings)
    verify_engines(settings, engines)
    web = load_web_settings()  # falla al arrancar si falta NUKYRO_ORIGIN
    app.state.origin = web.origin
    app.state.documents = entry_service.load_documents(web.documents_path)
    app.state.engines = engines
    log.info("API lista: %d conexiones verificadas", len(engines))
    yield
    for engine in engines.values():
        engine.dispose()


def create_app() -> FastAPI:
    # Sin documentación pública: el contrato vive en el repositorio
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    security.install(app)

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        # Solo método, ruta y estado: ni cookies, ni cuerpo, ni query
        response = await call_next(request)
        log.info("%s %s %d", request.method, request.url.path, response.status_code)
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        code = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
        }.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, "Solicitud no válida")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # No se devuelve la entrada ni el detalle de los campos
        return error_response(422, "validation_error", "La solicitud no es válida")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        log.error("Error no controlado: %s", type(exc).__name__)  # sin traza ni mensaje
        return error_response(500, "internal_error", "Error interno")

    @app.get("/api/v1/health")
    def health(request: Request):
        try:
            with request.app.state.engines["api"].connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            log.error("Health: la base no responde (%s)", type(exc).__name__)
            return error_response(503, "database_unavailable", "La base de datos no responde")
        return {"status": "ok"}

    app.include_router(entry_router)
    app.include_router(simulation_router)
    app.include_router(assessment_router)
    return app


app = create_app()
