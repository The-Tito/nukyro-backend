"""Rutas de la cuenta. Sin lógica: validan, llaman al servicio y limpian la cookie anónima."""

from fastapi import APIRouter, HTTPException, Request, Response

from nukyro.auth import clear_cookie, require_identity
from nukyro.identity_provider import ProviderUnavailable
from nukyro.modules.account import service
from nukyro.modules.account.schemas import AccountOut, LoginIn, LoginOut
from nukyro.security import cookie_secret

router = APIRouter(prefix="/api/v1/account")


def engine(request: Request):
    return request.app.state.engines["api"]


def confirm_new_identity(request: Request) -> None:
    require_identity(request)
    provider = getattr(request.app.state, "identity_provider", None)
    if provider is None:
        return
    token = request.headers["authorization"].partition(" ")[2].strip()
    try:
        exists = provider.has_identity(token)
    except ProviderUnavailable:
        raise HTTPException(503) from None
    if not exists:
        raise HTTPException(401)


@router.post("/login", response_model=LoginOut)
def login(request: Request, response: Response, body: LoginIn | None = None):
    identity = require_identity(request)
    result = service.login(
        engine(request),
        identity,
        body or LoginIn(),
        cookie_secret(request),
        recheck_identity=lambda: confirm_new_identity(request),
    )
    clear_cookie(response)  # tras iniciar sesión, la cookie anónima ya no sirve
    return result


@router.get("", response_model=AccountOut)
def get_account(request: Request):
    return service.get_account(engine(request), require_identity(request))
