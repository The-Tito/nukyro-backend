"""Reglas del recorrido de entrada (P1 y P2 del modelo de datos). Una transacción por operación."""

import json
from datetime import UTC
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

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


def create_participant(engine: Engine, documents: dict, body, secret: str | None):
    """Devuelve (estado, secreto). Con cookie válida no crea otro participante."""
    versions = current_versions(documents)
    if (
        not body.age_confirmed
        or body.privacy_notice_version != versions["privacy_notice"]
        or body.terms_version != versions["terms"]
    ):
        raise HTTPException(422)
    with engine.begin() as conn:
        if secret and (existing := queries.touch_participant(conn, hash_secret(secret))):
            # Si cambió la versión de un documento, se registra la nueva aceptación (RF-073)
            queries.insert_acceptances(
                conn, existing, body.privacy_notice_version, body.terms_version
            )
            return "existing", secret
        secret = new_secret()
        participant = queries.insert_participant(conn, hash_secret(secret))
        queries.insert_acceptances(
            conn, participant, body.privacy_notice_version, body.terms_version
        )
    return "created", secret


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
        "current_node": {
            "key": row["node_key"],
            "type": row["node_type"],
            "title": row["node_title"],
            "body": row["node_body"],
        },
    }


def start_session(engine: Engine, documents: dict, secret: str, body) -> dict:
    versions = current_versions(documents)
    try:
        return _start_session(engine, versions, secret, body)
    except IntegrityError as exc:
        # Solo el trigger de RN-15 (la versión se retiró entre la consulta y el INSERT) es un 404.
        # Un CHECK trae nombre de restricción; cualquier otro fallo es un 500 que se registra.
        diag = getattr(exc.orig, "diag", None)
        if getattr(exc.orig, "sqlstate", None) == "23514" and not (diag and diag.constraint_name):
            raise HTTPException(404) from None
        raise


def _start_session(engine: Engine, versions: dict, secret: str, body) -> dict:
    with engine.begin() as conn:
        participant = queries.lock_participant(conn, hash_secret(secret))  # primero el participante
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


def get_session(engine: Engine, secret: str, session_id: str) -> dict:
    try:
        session = UUID(session_id)
    except ValueError:
        raise HTTPException(404) from None  # igual que lo ajeno o inexistente
    with engine.begin() as conn:
        participant = queries.touch_participant(conn, hash_secret(secret))
        if participant is None:
            raise HTTPException(401)
        row = queries.session_by_id(conn, participant, session)
    if row is None:
        raise HTTPException(404)
    return _view(row)


def list_sessions(engine: Engine, secret: str) -> dict:
    with engine.begin() as conn:
        participant = queries.touch_participant(conn, hash_secret(secret))
        if participant is None:
            raise HTTPException(401)
        return {"sessions": [_view(r) for r in queries.sessions_of(conn, participant)]}
