"""Titularidad y transacciones de derechos del participante (RF-078, RF-079)."""

from fastapi import HTTPException
from sqlalchemy import Connection, Engine

from nukyro.auth import Auth
from nukyro.modules.account import queries as account_queries
from nukyro.modules.entry import queries as entry_queries
from nukyro.modules.rights import queries


def lock_owner(conn: Connection, auth: Auth, *, anonymous_only: bool = False):
    if auth.identity is not None:
        # Igual que block_account: primero la cuenta, después el participante.
        account = account_queries.lock_account(conn, auth.identity.sub)
        if account is None:
            raise HTTPException(401)
        if account["status"] == "blocked":
            raise HTTPException(403, detail="account_blocked")
        if anonymous_only:
            raise HTTPException(403)
    participant = entry_queries.lock_participant(conn, auth)
    if participant is None:
        raise HTTPException(401)
    return participant


def export_anonymous_data(engine: Engine, auth: Auth) -> dict:
    with engine.begin() as conn:
        participant = lock_owner(conn, auth, anonymous_only=True)
        return queries.export_data(conn, participant)


def erase_anonymous_data(engine: Engine, auth: Auth) -> None:
    with engine.begin() as conn:
        participant = lock_owner(conn, auth, anonymous_only=True)
        queries.erase_data(conn, participant)


def oppose_statistics(engine: Engine, auth: Auth) -> None:
    with engine.begin() as conn:
        participant = lock_owner(conn, auth)
        queries.oppose_statistics(conn, participant)
