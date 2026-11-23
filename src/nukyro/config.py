"""Configuración desde variables de entorno. Falla al arrancar si falta alguna."""

import os
from dataclasses import dataclass

from nukyro.identity import OidcSettings

# Rol de conexión de la aplicación -> rol de grupo de la base (bd/schema.sql)
ROLES = ("api", "admin", "jobs", "analytics")


@dataclass(frozen=True)
class RoleLogin:
    user: str
    password: str = ""

    def __repr__(self) -> str:  # nunca imprime el secreto
        return f"RoleLogin(user={self.user!r})"


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    dbname: str
    logins: dict[str, RoleLogin]


def _required(env: dict[str, str], name: str) -> str:
    value = env.get(name, "")
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}")
    return value


def _load(env: dict[str, str], roles: tuple[str, ...]) -> Settings:
    logins = {}
    for role in roles:
        prefix = f"NUKYRO_DB_{role.upper()}"
        logins[role] = RoleLogin(
            _required(env, f"{prefix}_USER"), _required(env, f"{prefix}_PASSWORD")
        )
    return Settings(
        host=_required(env, "NUKYRO_DB_HOST"),
        port=int(env.get("NUKYRO_DB_PORT") or 5432),
        dbname=_required(env, "NUKYRO_DB_NAME"),
        logins=logins,
    )


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Los cuatro usuarios de la API. El owner del esquema nunca llega aquí."""
    return _load(os.environ if env is None else env, ROLES)


def load_owner_settings(env: dict[str, str] | None = None) -> Settings:
    """Solo para Alembic: un único login, el owner del esquema."""
    return _load(os.environ if env is None else env, ("owner",))


def load_admin_settings(env: dict[str, str] | None = None) -> Settings:
    """Solo para la siembra del escenario de demostración: el login del rol admin."""
    return _load(os.environ if env is None else env, ("admin",))


@dataclass(frozen=True)
class WebSettings:
    origin: str  # Origin exacto que se acepta en las escrituras (CSRF)
    documents_path: str  # JSON con el aviso y los documentos vigentes


def load_web_settings(env: dict[str, str] | None = None) -> WebSettings:
    env = os.environ if env is None else env
    return WebSettings(
        origin=_required(env, "NUKYRO_ORIGIN"),
        documents_path=env.get("NUKYRO_DOCUMENTS_PATH") or "/app/demo/documents.json",
    )


def load_oidc_settings(env: dict[str, str] | None = None) -> OidcSettings:
    """Emisor de identidad (D-34). Sin JWKS explícito, el de Cognito (`/.well-known/jwks.json`)."""
    env = os.environ if env is None else env
    issuer = _required(env, "NUKYRO_OIDC_ISSUER").rstrip("/")
    return OidcSettings(
        issuer=issuer,
        audience=_required(env, "NUKYRO_OIDC_AUDIENCE"),
        jwks_url=env.get("NUKYRO_OIDC_JWKS_URL") or f"{issuer}/.well-known/jwks.json",
    )
