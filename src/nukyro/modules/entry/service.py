"""Reglas del recorrido de entrada (P1 y P2 del modelo de datos). Una transacción por operación."""

import json
from datetime import UTC

from fastapi import HTTPException
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from nukyro.auth import Auth
from nukyro.modules.assessment.phases import phases
from nukyro.modules.entry import queries
from nukyro.security import hash_secret, new_secret


def load_documents(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def current_versions(documents: dict) -> dict[str, str]:
    return {d["type"]: d["version"] for d in documents["documents"]}


def entry(engine: Engine, documents: dict) -> dict:
    with engine.begin() as conn:
        scenarios = [dict(r) for r in queries.published_scenarios(conn)]
    return {**documents, "scenarios": scenarios}


def create_participant(engine: Engine, documents: dict, body, auth: Auth | None):
    """Devuelve (estado, secreto). El secreto es None con cuenta: no hay cookie que entregar.

    Con cookie válida no crea otro participante. Con token, el participante nace ligado a la
    cuenta y sin secreto (la cuenta ya existe porque pasó por /account/login)."""
    versions = current_versions(documents)
    if (
        not body.age_confirmed
        or body.privacy_notice_version != versions["privacy_notice"]
        or body.terms_version != versions["terms"]
    ):
        raise HTTPException(422)
    with engine.begin() as conn:
        if auth is not None and auth.identity is not None:
            return _create_for_account(conn, auth, body), None
        if auth is not None and (existing := queries.touch_participant(conn, auth)):
            # Si cambió la versión de un documento, se registra la nueva aceptación (RF-073)
            queries.insert_acceptances(
                conn, existing, body.privacy_notice_version, body.terms_version
            )
            return "existing", auth.secret
        secret = new_secret()
        participant = queries.insert_participant(conn, hash_secret(secret))
        queries.insert_acceptances(
            conn, participant, body.privacy_notice_version, body.terms_version
        )
    return "created", secret


def _create_for_account(conn, auth: Auth, body) -> str:
    sub = auth.identity.sub
    status = conn.execute(
        text("SELECT status FROM nukyro.accounts WHERE cognito_sub = :s"), {"s": sub}
    ).scalar_one_or_none()
    if status is None:
        raise HTTPException(401)  # falta POST /account/login
    if status == "blocked":
        raise HTTPException(403, detail="account_blocked")
    participant = queries.insert_account_participant(conn, sub)
    state = "created"
    if participant is None:  # ya existía (o lo creó otra petición a la vez)
        participant = queries.touch_participant(conn, auth)
        state = "existing"
    queries.insert_acceptances(conn, participant, body.privacy_notice_version, body.terms_version)
    return state


def _view(row) -> dict:
    return {
        "id": row["id"],
        "scenario": {
            "key": row["scenario_key"],
            "title": row["scenario_title"],
            "version_number": row["version_number"],
            "introduction": row["scenario_introduction"],
        },
        "started_at": row["started_at"].astimezone(UTC),
        "is_first_session": row["is_first_session"],
        "state": row["state"],
        "phases": [
            {"phase": name, "at": at.astimezone(UTC)}
            for name, at in phases(
                row["started_at"],
                row["pretest_completed_at"],
                row["outcome_reached_at"],
                row["completed_at"],
            )
        ],
        "current_node": {
            "key": row["node_key"],
            "type": row["node_type"],
            "title": row["node_title"],
            "body": row["node_body"],
        },
    }


def start_session(engine: Engine, documents: dict, auth: Auth, body) -> dict:
    versions = current_versions(documents)
    try:
        return _start_session(engine, versions, auth, body)
    except IntegrityError as exc:
        # Solo el trigger de RN-15 (la versión se retiró entre la consulta y el INSERT) es un 404.
        # Un CHECK trae nombre de restricción; cualquier otro fallo es un 500 que se registra.
        diag = getattr(exc.orig, "diag", None)
        if getattr(exc.orig, "sqlstate", None) == "23514" and not (diag and diag.constraint_name):
            raise HTTPException(404) from None
        raise


def _start_session(engine: Engine, versions: dict, auth: Auth, body) -> dict:
    with engine.begin() as conn:
        participant = queries.lock_participant(conn, auth)  # primero el participante
        if participant is None:
            raise HTTPException(401)
        if (
            queries.current_acceptances(
                conn, participant, versions["privacy_notice"], versions["terms"]
            )
            != 3
        ):
            raise HTTPException(422)
        version = queries.published_version(conn, body.scenario_key)
        if version is None:
            raise HTTPException(404)
        intro = queries.intro_nodes(conn, version)
        if len(intro) != 1:
            raise RuntimeError("la versión publicada debe tener un único nodo intro")
        session = queries.insert_session(
            conn, participant, version, intro[0], body.self_reported_first
        )
        queries.insert_initial_state(conn, session, version, intro[0])
        conn.execute(
            text("UPDATE nukyro.participants SET last_activity_at = now() WHERE id = :p"),
            {"p": participant},
        )
        return _view(queries.session_by_id(conn, participant, session))


def list_sessions(engine: Engine, auth: Auth) -> dict:
    with engine.begin() as conn:
        participant = queries.touch_participant(conn, auth)
        if participant is None:
            raise HTTPException(401)
        return {"sessions": [_view(r) for r in queries.sessions_of(conn, participant)]}
