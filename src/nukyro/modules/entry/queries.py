"""SQL explícito del recorrido de entrada. Cada función recibe la conexión de una transacción."""

from fastapi import HTTPException
from sqlalchemy import Connection, text

from nukyro.auth import Auth

# Estado calculado de la sesión (modelo de datos §4)
STATE = (
    "CASE WHEN s.completed_at IS NOT NULL THEN 'completed' "
    "WHEN s.outcome_reached_at IS NOT NULL THEN 'outcome_reached' "
    "WHEN s.pretest_completed_at IS NOT NULL THEN 'in_scenario' ELSE 'started' END"
)
SESSION_SELECT = f"""
    SELECT s.id, sc.key AS scenario_key, v.title AS scenario_title, v.version_number,
           v.introduction AS scenario_introduction,
           s.started_at, s.pretest_completed_at, s.outcome_reached_at, s.completed_at,
           s.is_first_session, {STATE} AS state,
           n.key AS node_key, n.node_type AS node_type, n.title AS node_title, n.body AS node_body
      FROM nukyro.sessions s
      JOIN nukyro.scenario_versions v ON v.id = s.scenario_version_id
      JOIN nukyro.scenarios sc ON sc.id = v.scenario_id
      JOIN nukyro.nodes n ON n.id = s.current_node_id
"""


def published_scenarios(conn: Connection):
    return (
        conn.execute(
            text(
                "SELECT sc.key, v.title, v.version_number FROM nukyro.scenarios sc "
                "JOIN nukyro.scenario_versions v "
                "ON v.scenario_id = sc.id AND v.status = 'published' "
                "ORDER BY sc.key"
            )
        )
        .mappings()
        .all()
    )


def insert_participant(conn: Connection, secret_hash: bytes):
    return conn.execute(
        text("INSERT INTO nukyro.participants (secret_hash) VALUES (:h) RETURNING id"),
        {"h": secret_hash},
    ).scalar_one()


def insert_account_participant(conn: Connection, sub: str):
    """Participante de la cuenta, sin secreto. None si ya existía (otra petición lo creó)."""
    return conn.execute(
        text(
            "INSERT INTO nukyro.participants (account_id) "
            "SELECT a.id FROM nukyro.accounts a WHERE a.cognito_sub = :s AND a.status = 'active' "
            "ON CONFLICT (account_id) DO NOTHING RETURNING id"
        ),
        {"s": sub},
    ).scalar_one_or_none()


def insert_acceptances(conn: Connection, participant, privacy: str, terms: str) -> None:
    conn.execute(
        text(
            "INSERT INTO nukyro.document_acceptances "
            "(participant_id, document_type, document_version) "
            "VALUES (:p, 'age_18_plus', NULL), (:p, 'privacy_notice', :pv), (:p, 'terms', :tv) "
            "ON CONFLICT DO NOTHING"
        ),
        {"p": participant, "pv": privacy, "tv": terms},
    )


def _explain_missing(conn: Connection, sub: str):
    """Token válido sin participante activo: cuenta ausente, bloqueada o sin aceptar documentos."""
    status = conn.execute(
        text("SELECT status FROM nukyro.accounts WHERE cognito_sub = :s"), {"s": sub}
    ).scalar_one_or_none()
    if status is None:
        raise HTTPException(401)  # nunca inició sesión: falta POST /account/login
    if status == "blocked":
        raise HTTPException(403, detail="account_blocked")
    raise HTTPException(409, detail="documents_required")  # cuenta sin participante


def touch_participant(conn: Connection, auth: Auth):
    """Autentica y renueva la actividad; devuelve el id o None (cookie desconocida)."""
    if auth.identity is None:
        return conn.execute(
            text(
                "UPDATE nukyro.participants SET last_activity_at = now() "
                "WHERE secret_hash = :h RETURNING id"
            ),
            {"h": auth.secret_hash},
        ).scalar_one_or_none()
    found = conn.execute(
        text(
            "UPDATE nukyro.participants p SET last_activity_at = now() FROM nukyro.accounts a "
            "WHERE a.id = p.account_id AND a.cognito_sub = :s AND a.status = 'active' "
            "RETURNING p.id"
        ),
        {"s": auth.identity.sub},
    ).scalar_one_or_none()
    if found is None:
        _explain_missing(conn, auth.identity.sub)
    return found


def lock_participant(conn: Connection, auth: Auth):
    """Primer bloqueo de toda operación sobre sesiones: el participante."""
    if auth.identity is None:
        return conn.execute(
            text("SELECT id FROM nukyro.participants WHERE secret_hash = :h FOR NO KEY UPDATE"),
            {"h": auth.secret_hash},
        ).scalar_one_or_none()
    found = conn.execute(
        text(
            "SELECT p.id FROM nukyro.participants p JOIN nukyro.accounts a ON a.id = p.account_id "
            "WHERE a.cognito_sub = :s AND a.status = 'active' FOR NO KEY UPDATE OF p"
        ),
        {"s": auth.identity.sub},
    ).scalar_one_or_none()
    if found is None:
        _explain_missing(conn, auth.identity.sub)
    return found


def current_acceptances(conn: Connection, participant, privacy: str, terms: str) -> int:
    return conn.execute(
        text(
            "SELECT count(DISTINCT document_type) FROM nukyro.document_acceptances "
            "WHERE participant_id = :p AND (document_type = 'age_18_plus' "
            "OR (document_type = 'privacy_notice' AND document_version = :pv) "
            "OR (document_type = 'terms' AND document_version = :tv))"
        ),
        {"p": participant, "pv": privacy, "tv": terms},
    ).scalar_one()


def published_version(conn: Connection, scenario_key: str):
    """Versión publicada del escenario (el rol de la API no puede bloquearla con FOR SHARE)."""
    return conn.execute(
        text(
            "SELECT v.id FROM nukyro.scenarios sc "
            "JOIN nukyro.scenario_versions v "
            "ON v.scenario_id = sc.id AND v.status = 'published' "
            "WHERE sc.key = :k"
        ),
        {"k": scenario_key},
    ).scalar_one_or_none()


def intro_nodes(conn: Connection, version):
    return (
        conn.execute(
            text("SELECT id FROM nukyro.nodes WHERE version_id = :v AND node_type = 'intro'"),
            {"v": version},
        )
        .scalars()
        .all()
    )


def insert_session(conn: Connection, participant, version, node, first: bool):
    # Solo las columnas permitidas; started_at e id los pone el servidor
    return conn.execute(
        text(
            "INSERT INTO nukyro.sessions (participant_id, scenario_version_id, current_node_id, "
            "self_reported_first) VALUES (:p, :v, :n, :f) RETURNING id"
        ),
        {"p": participant, "v": version, "n": node, "f": first},
    ).scalar_one()


def insert_initial_state(conn: Connection, session, version, node) -> None:
    conn.execute(
        text(
            "INSERT INTO nukyro.session_variables "
            "(session_id, scenario_version_id, variable_id, value) "
            "SELECT :s, :v, id, initial_value FROM nukyro.state_variables WHERE version_id = :v"
        ),
        {"s": session, "v": version},
    )
    conn.execute(
        text(
            "INSERT INTO nukyro.session_steps (session_id, scenario_version_id, node_id, seq) "
            "VALUES (:s, :v, :n, 1)"
        ),
        {"s": session, "v": version, "n": node},
    )


def session_by_id(conn: Connection, participant, session):
    return (
        conn.execute(
            text(SESSION_SELECT + " WHERE s.id = :s AND s.participant_id = :p"),
            {"s": session, "p": participant},
        )
        .mappings()
        .one_or_none()
    )


def sessions_of(conn: Connection, participant):
    return (
        conn.execute(
            text(SESSION_SELECT + " WHERE s.participant_id = :p ORDER BY s.started_at, s.id"),
            {"p": participant},
        )
        .mappings()
        .all()
    )
