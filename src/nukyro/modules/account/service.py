"""Cuenta con Cognito (RF-074 a RF-076, P10). Una transacción por operación.

Orden de bloqueo: cuenta, participante del navegador, participante de la cuenta, sesiones.
"""

from fastapi import HTTPException
from sqlalchemy import Engine

from nukyro.identity import Identity
from nukyro.modules.account import queries
from nukyro.security import hash_secret

MAX_NICKNAME = 40
MAX_EMAIL = 254


def login(engine: Engine, identity: Identity, body, secret: str | None) -> dict:
    """Crea la cuenta si es nueva (idempotente), la sincroniza y vincula el progreso del navegador.

    Con una cuenta bloqueada no hace nada (D-20). Repetir la llamada no cambia nada más."""
    if not identity.email_verified:
        raise HTTPException(403)  # RF-074: la cuenta exige el correo verificado
    nickname, email = identity.nickname, identity.email
    if not email or len(email) > MAX_EMAIL or not nickname or len(nickname) > MAX_NICKNAME:
        raise HTTPException(422)  # el token debe traer correo y nickname válidos
    secret_hash = hash_secret(secret) if secret else None
    with engine.begin() as conn:
        created = queries.insert_account(
            conn,
            identity.sub,
            email,
            nickname,
            body.newsletter_opt_in,
            body.surveys_opt_in,
        )
        account = queries.lock_account(conn, identity.sub)
        if account["status"] == "blocked":
            raise HTTPException(403, detail="account_blocked")
        if created is not None:
            queries.insert_registration_consents(
                conn, account["id"], body.newsletter_opt_in, body.surveys_opt_in
            )
        else:
            queries.refresh_account(conn, account["id"], email, nickname)
        linked = queries.link_participant(conn, account["id"], secret_hash) != "none"
        return {
            "nickname": nickname,
            "has_participant": queries.has_participant(conn, account["id"]),
            "linked": linked,
        }


def get_account(engine: Engine, identity: Identity) -> dict:
    with engine.begin() as conn:
        row = queries.account_by_sub(conn, identity.sub)
    if row is None:
        raise HTTPException(401)  # nunca inició sesión: falta POST /account/login
    if row["status"] == "blocked":
        raise HTTPException(403, detail="account_blocked")
    return {k: row[k] for k in ("nickname", "email", "newsletter_opt_in", "surveys_opt_in")}
