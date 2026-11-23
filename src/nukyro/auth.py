"""Quién hace la petición: token de identidad de Cognito (con cuenta) o cookie (sin cuenta).

ADR-002 §6 y ADR-008: el servidor resuelve al participante y filtra por él. El token manda sobre
la cookie; un token inválido nunca cae de vuelta a la cookie.
"""

from dataclasses import dataclass

from fastapi import HTTPException, Request, Response

from nukyro.identity import Identity, InvalidToken, WrongGroup
from nukyro.security import COOKIE, cookie_secret, hash_secret, set_cookie


@dataclass(frozen=True)
class Auth:
    secret: str | None = None  # navegador sin cuenta
    identity: Identity | None = None  # persona con cuenta

    @property
    def secret_hash(self) -> bytes:
        assert self.secret is not None
        return hash_secret(self.secret)


def token_identity(request: Request) -> Identity | None:
    """La identidad del encabezado Authorization, o None si no viene. 401 o 403 si no sirve."""
    header = request.headers.get("authorization")
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401)
    try:
        return request.app.state.verifier.verify(token.strip())
    except WrongGroup:
        raise HTTPException(403) from None  # quien administra no es participante
    except InvalidToken:
        raise HTTPException(401) from None


def authenticate(request: Request, *, required: bool = True) -> Auth | None:
    identity = token_identity(request)
    if identity is not None:
        return Auth(identity=identity)
    secret = cookie_secret(request)
    if secret is not None:
        return Auth(secret=secret)
    if required:
        raise HTTPException(401)
    return None


def require_identity(request: Request) -> Identity:
    """Rutas de cuenta: solo con token, nunca con la cookie."""
    identity = token_identity(request)
    if identity is None:
        raise HTTPException(401)
    return identity


def refresh_cookie(response: Response, auth: Auth) -> None:
    if auth.secret is not None:  # con token no hay cookie que renovar
        set_cookie(response, auth.secret)


def clear_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="lax")
