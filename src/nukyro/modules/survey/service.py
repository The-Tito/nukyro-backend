"""Encuesta no vinculada (D-29, ADR-007). La escritura es la función submit_survey de la base."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from nukyro.auth import Auth
from nukyro.modules.entry import queries as entry_queries

NOTE = (
    "Esta encuesta es voluntaria y puedes omitirla sin consecuencias. Sirve para mejorar el "
    "simulador, no califica tu desempeño y se guarda sin tu identificador de participante ni de "
    "sesión. Lee el aviso de privacidad para conocer cómo se usan los datos."
)
NOTICE_URL = "/api/v1/entry"
SCALES = (
    ("usefulness", "¿Qué tan útil te pareció la simulación?", True),
    ("clarity", "¿Qué tan claras te parecieron las situaciones y las alternativas?", False),
    ("decision_impact", "¿Qué tanto cambió esta experiencia la forma en que decidirías?", False),
    (
        "causal_understanding",
        "¿Qué tanto entendiste cómo tus decisiones llevaron a lo ocurrido?",
        False,
    ),
    ("summary_usefulness", "¿Qué tan útil te pareció el resumen final?", False),
    ("would_repeat", "¿Qué tanto repetirías una simulación como esta?", False),
)
# SQLSTATE de submit_survey y su respuesta HTTP
ERRORS = {"42501": 403, "55000": 409, "23505": 409, "P0002": 404, "23514": 422}


def _session_id(session_id: str) -> UUID:
    try:
        return UUID(session_id)
    except ValueError:
        raise HTTPException(404) from None


def _authenticate(engine: Engine, auth: Auth):
    """Renueva la actividad del participante en su propia transacción, ya confirmada. Así el envío
    no comparte transacción (ni xmin) con ninguna otra escritura (ADR-007)."""
    with engine.begin() as conn:
        participant = entry_queries.touch_participant(conn, auth)
    if participant is None:
        raise HTTPException(401)
    return participant


def _state(conn, participant, session):
    """Estado de la sesión del participante; None si no es suya."""
    return (
        conn.execute(
            text(
                "SELECT s.completed_at IS NOT NULL AS completed, s.survey_answered, "
                "p.exclude_from_stats, coalesce(a.status = 'blocked', false) AS blocked "
                "FROM nukyro.sessions s JOIN nukyro.participants p ON p.id = s.participant_id "
                "LEFT JOIN nukyro.accounts a ON a.id = p.account_id "
                "WHERE s.id = :s AND s.participant_id = :p"
            ),
            {"s": session, "p": participant},
        )
        .mappings()
        .one_or_none()
    )


def get_survey(engine: Engine, auth: Auth, session_id: str) -> dict:
    session = _session_id(session_id)
    participant = _authenticate(engine, auth)
    with engine.connect() as conn:
        row = _state(conn, participant, session)
    if row is None:
        raise HTTPException(404)
    # Al opuesto, o sin terminar, o ya respondida: no se ofrece (D-29)
    if (
        not row["completed"]
        or row["survey_answered"]
        or row["exclude_from_stats"]
        or row["blocked"]
    ):
        return {"available": False}
    return {
        "available": True,
        "note": NOTE,
        "notice_url": NOTICE_URL,
        "can_skip": True,
        "questions": [
            {"key": k, "prompt": p, "required": r, "min": 1, "max": 5} for k, p, r in SCALES
        ],
    }


def submit_survey(engine: Engine, auth: Auth, session_id: str, body) -> dict:
    session = _session_id(session_id)
    participant = _authenticate(engine, auth)
    values = {k: getattr(body, k) for k, _, _ in SCALES}
    try:
        with engine.begin() as conn:
            if _state(conn, participant, session) is None:
                raise HTTPException(404)
            # Única escritura de esta transacción: la función de la base (sin touch_session)
            conn.execute(
                text(
                    "SELECT nukyro.submit_survey(:s, CAST(:u AS smallint), CAST(:c AS smallint), "
                    "CAST(:d AS smallint), CAST(:k AS smallint), CAST(:m AS smallint), "
                    "CAST(:w AS smallint))"
                ),
                {
                    "s": session,
                    "u": values["usefulness"],
                    "c": values["clarity"],
                    "d": values["decision_impact"],
                    "k": values["causal_understanding"],
                    "m": values["summary_usefulness"],
                    "w": values["would_repeat"],
                },
            )
    except DBAPIError as error:
        status = ERRORS.get(getattr(error.orig, "sqlstate", None))
        if status is None:
            raise
        raise HTTPException(status) from None
    return {"submitted": True}
