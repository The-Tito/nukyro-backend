"""Rutas de la cuenta. Sin lógica: validan, llaman al servicio y limpian la cookie anónima."""

from fastapi import APIRouter, Request, Response

from nukyro.auth import clear_cookie, require_identity
from nukyro.modules.account import service
from nukyro.modules.account.schemas import AccountOut, LoginIn, LoginOut
from nukyro.security import cookie_secret

router = APIRouter(prefix="/api/v1/account")


def engine(request: Request):
    return request.app.state.engines["api"]


@router.post("/login", response_model=LoginOut)
def login(request: Request, response: Response, body: LoginIn | None = None):
    identity = require_identity(request)
    result = service.login(
        engine(request),
        identity,
        body or LoginIn(),
        cookie_secret(request),
        recheck_identity=lambda: require_identity(request),
    )
    clear_cookie(response)  # tras iniciar sesión, la cookie anónima ya no sirve
    return result


@router.get("", response_model=AccountOut)
def get_account(request: Request):
    return service.get_account(engine(request), require_identity(request))
