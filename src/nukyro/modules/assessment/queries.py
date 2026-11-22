"""SQL explícito de las evaluaciones (P6). Las correctas solo se leen aquí, para calificar."""

from sqlalchemy import Connection, text


def _all(conn, sql, **params):
    return conn.execute(text(sql), params).mappings().all()


def session_row(conn: Connection, participant, session, lock: bool):
    """La sesión del participante con sus hitos; `lock` la bloquea (tras el participante)."""
    return (
        conn.execute(
            text(
                "SELECT id, scenario_version_id AS version, pretest_completed_at, "
                "outcome_reached_at, completed_at FROM nukyro.sessions "
                "WHERE id = :s AND participant_id = :p" + (" FOR UPDATE" if lock else "")
            ),
            {"s": session, "p": participant},
        )
        .mappings()
        .one_or_none()
    )


def hitos(conn: Connection, session):
    return (
        conn.execute(
            text(
                "SELECT scenario_version_id AS version, outcome_reached_at, completed_at "
                "FROM nukyro.sessions WHERE id = :s"
            ),
            {"s": session},
        )
        .mappings()
        .one()
    )


def question_rows(conn: Connection, version):
    """Conjuntos de la versión con sus preguntas (sin preguntas: question_id nulo)."""
    return _all(
        conn,
        "SELECT st.id AS set_id, st.set_type, st.requires_all_answers, q.id AS question_id, "
        "q.key, q.prompt, q.requires_node_id FROM nukyro.question_sets st "
        "LEFT JOIN nukyro.questions q ON q.question_set_id = st.id "
        "WHERE st.version_id = :v ORDER BY st.set_type, q.position, q.key",
        v=version,
    )


def path_nodes(conn: Connection, session) -> set:
    rows = _all(conn, "SELECT node_id FROM nukyro.session_steps WHERE session_id = :s", s=session)
    return {r["node_id"] for r in rows}


def event_targets(conn: Connection, session) -> set:
    """Destinos de los eventos activados en la sesión (RF-058)."""
    rows = _all(
        conn,
        "SELECT r.target_node_id FROM nukyro.session_events e "
        "JOIN nukyro.rules r ON r.id = e.rule_id WHERE e.session_id = :s AND r.rule_type = 'event'",
        s=session,
    )
    return {r["target_node_id"] for r in rows}


def attempts(conn: Connection, session) -> dict:
    rows = _all(
        conn,
        "SELECT a.id, a.question_set_id AS set_id, a.submitted_at, a.score "
        "FROM nukyro.assessment_attempts a WHERE a.session_id = :s",
        s=session,
    )
    return {r["set_id"]: r for r in rows}


def options(conn: Connection, session, set_id):
    """Opciones en un orden fijo por sesión que no revela la correcta."""
    return _all(
        conn,
        "SELECT o.question_id, o.key, o.label FROM nukyro.question_options o "
        "JOIN nukyro.questions q ON q.id = o.question_id WHERE q.question_set_id = :st "
        "ORDER BY md5(CAST(:s AS text) || CAST(o.id AS text))",
        st=set_id,
        s=session,
    )


def answers(conn: Connection, attempt) -> dict:
    rows = _all(
        conn,
        "SELECT a.question_id, o.key FROM nukyro.assessment_answers a "
        "JOIN nukyro.question_options o ON o.id = a.option_id WHERE a.attempt_id = :a",
        a=attempt,
    )
    return {r["question_id"]: r["key"] for r in rows}


def option_id(conn: Connection, question, key):
    return conn.execute(
        text("SELECT id FROM nukyro.question_options WHERE question_id = :q AND key = :k"),
        {"q": question, "k": key},
    ).scalar_one_or_none()


def ensure_attempt(conn: Connection, session, version, set_id, existing):
    """El intento del conjunto; la sesión ya está bloqueada, así que no hay carrera al crearlo."""
    if existing is not None:
        return existing["id"]
    return conn.execute(
        text(
            "INSERT INTO nukyro.assessment_attempts "
            "(session_id, scenario_version_id, question_set_id) VALUES (:s, :v, :q) RETURNING id"
        ),
        {"s": session, "v": version, "q": set_id},
    ).scalar_one()


def upsert_answer(conn: Connection, attempt, set_id, question, option) -> None:
    conn.execute(
        text(
            "INSERT INTO nukyro.assessment_answers "
            "(attempt_id, question_set_id, question_id, option_id) "
            "VALUES (:a, :st, :q, :o) ON CONFLICT (attempt_id, question_id) "
            "DO UPDATE SET option_id = EXCLUDED.option_id, answered_at = now()"
        ),
        {"a": attempt, "st": set_id, "q": question, "o": option},
    )


def tally(conn: Connection, attempt):
    """(respondidas, correctas) del intento; solo para calificar."""
    row = conn.execute(
        text(
            "SELECT count(*) AS answered, count(*) FILTER (WHERE o.is_correct) AS correct "
            "FROM nukyro.assessment_answers a JOIN nukyro.question_options o ON o.id = a.option_id "
            "WHERE a.attempt_id = :a"
        ),
        {"a": attempt},
    ).one()
    return row.answered, row.correct


def submit_attempt(conn: Connection, attempt, answered, correct, score) -> None:
    conn.execute(
        text(
            "UPDATE nukyro.assessment_attempts SET submitted_at = now(), answered_count = :n, "
            "correct_count = :c, score = :x WHERE id = :a"
        ),
        {"a": attempt, "n": answered, "c": correct, "x": score},
    )


def touch_session(conn: Connection, session) -> None:
    conn.execute(
        text("UPDATE nukyro.sessions SET last_activity_at = now() WHERE id = :s"), {"s": session}
    )


def mark_pretest(conn: Connection, session) -> None:
    conn.execute(
        text(
            "UPDATE nukyro.sessions SET pretest_completed_at = now() "
            "WHERE id = :s AND pretest_completed_at IS NULL"
        ),
        {"s": session},
    )


def mark_completed(conn: Connection, session) -> None:
    conn.execute(
        text(
            "UPDATE nukyro.sessions SET completed_at = now() WHERE id = :s AND completed_at IS NULL"
        ),
        {"s": session},
    )
