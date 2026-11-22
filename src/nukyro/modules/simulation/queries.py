"""SQL explícito de la simulación (P5). Solo columnas permitidas al rol api."""

from sqlalchemy import Connection, text

from nukyro.modules.entry.queries import SESSION_SELECT


def lock_session(conn: Connection, participant, session):
    """Segundo bloqueo: la sesión, solo si es del participante."""
    return (
        conn.execute(
            text(
                "SELECT id, scenario_version_id AS version, current_node_id, "
                "pretest_completed_at FROM nukyro.sessions "
                "WHERE id = :s AND participant_id = :p FOR UPDATE"
            ),
            {"s": session, "p": participant},
        )
        .mappings()
        .one_or_none()
    )


def has_pretest(conn: Connection, version) -> bool:
    return conn.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM nukyro.question_sets "
            "WHERE version_id = :v AND set_type = 'pretest')"
        ),
        {"v": version},
    ).scalar_one()


def _all(conn, sql, **params):
    return conn.execute(text(sql), params).mappings().all()


def content_rows(conn: Connection, version) -> dict:
    v = {"v": version}
    q = lambda sql: _all(conn, sql, **v)  # noqa: E731
    return {
        "nodes": q(
            "SELECT n.id, n.key, n.node_type, d.requires_justification, "
            "coalesce(d.min_correct_reasons, 1) AS min_correct, dn.key AS default_next "
            "FROM nukyro.nodes n LEFT JOIN nukyro.decision_points d ON d.node_id = n.id "
            "LEFT JOIN nukyro.nodes dn ON dn.id = n.default_next_node_id WHERE n.version_id = :v"
        ),
        "variables": q(
            "SELECT id, key, initial_value, min_value, max_value "
            "FROM nukyro.state_variables WHERE version_id = :v"
        ),
        "options": q(
            "SELECT o.id, o.key, o.effects, n.key AS node_key, nx.key AS next_key "
            "FROM nukyro.options o JOIN nukyro.nodes n ON n.id = o.node_id "
            "LEFT JOIN nukyro.nodes nx ON nx.id = o.next_node_id "
            "WHERE o.version_id = :v ORDER BY o.position, o.key"
        ),
        "reasons": q(
            "SELECT r.id, r.key, r.is_correct, n.key AS node_key "
            "FROM nukyro.justification_reasons r JOIN nukyro.nodes n ON n.id = r.node_id "
            "WHERE r.version_id = :v ORDER BY r.position, r.key"
        ),
        "rules": q(
            "SELECT r.id, r.key, r.rule_type, r.priority, r.condition, r.relation_type, "
            "r.explanation, f.key AS node_key, t.key AS target_key "
            "FROM nukyro.rules r JOIN nukyro.nodes f ON f.id = r.from_node_id "
            "JOIN nukyro.nodes t ON t.id = r.target_node_id WHERE r.version_id = :v"
        ),
    }


def state_rows(conn: Connection, session) -> dict:
    s = {"s": session}
    q = lambda sql: _all(conn, sql, **s)  # noqa: E731
    return {
        "path": q(
            "SELECT n.key FROM nukyro.session_steps st JOIN nukyro.nodes n ON n.id = st.node_id "
            "WHERE st.session_id = :s ORDER BY st.seq"
        ),
        "values": q(
            "SELECT v.key, sv.value FROM nukyro.session_variables sv "
            "JOIN nukyro.state_variables v ON v.id = sv.variable_id WHERE sv.session_id = :s"
        ),
        "decisions": q(
            "SELECT d.id, n.key AS node_key, o.key AS option_key, d.justification_correct "
            "FROM nukyro.session_decisions d JOIN nukyro.nodes n ON n.id = d.node_id "
            "JOIN nukyro.options o ON o.id = d.option_id WHERE d.session_id = :s "
            "ORDER BY d.decided_at, n.key"
        ),
        "decision_reasons": q(
            "SELECT dr.session_decision_id AS decision, r.key "
            "FROM nukyro.session_decision_reasons dr "
            "JOIN nukyro.justification_reasons r ON r.id = dr.reason_id "
            "JOIN nukyro.session_decisions d ON d.id = dr.session_decision_id "
            "WHERE d.session_id = :s ORDER BY r.key"
        ),
        "effects": q(
            "SELECT e.session_decision_id AS decision, v.key, e.old_value, e.new_value "
            "FROM nukyro.session_effects e JOIN nukyro.state_variables v ON v.id = e.variable_id "
            "WHERE e.session_id = :s"
        ),
        "events": q(
            "SELECT e.id, r.key AS rule_key FROM nukyro.session_events e "
            "JOIN nukyro.rules r ON r.id = e.rule_id WHERE e.session_id = :s"
        ),
        "causes": q(
            "SELECT c.session_event_id AS event, n.key AS node_key "
            "FROM nukyro.session_event_causes c "
            "JOIN nukyro.session_decisions d ON d.id = c.session_decision_id "
            "JOIN nukyro.nodes n ON n.id = d.node_id WHERE c.session_id = :s"
        ),
    }


def insert_decision(conn, session, version, node, option, correct):
    return conn.execute(
        text(
            "INSERT INTO nukyro.session_decisions "
            "(session_id, scenario_version_id, node_id, option_id, justification_correct) "
            "VALUES (:s, :v, :n, :o, :c) RETURNING id"
        ),
        {"s": session, "v": version, "n": node, "o": option, "c": correct},
    ).scalar_one()


def insert_decision_reason(conn, decision, node, reason) -> None:
    conn.execute(
        text(
            "INSERT INTO nukyro.session_decision_reasons "
            "(session_decision_id, node_id, reason_id) VALUES (:d, :n, :r)"
        ),
        {"d": decision, "n": node, "r": reason},
    )


def insert_effect(conn, decision, session, variable, old, new) -> None:
    conn.execute(
        text(
            "INSERT INTO nukyro.session_effects "
            "(session_decision_id, session_id, variable_id, old_value, new_value) "
            "VALUES (:d, :s, :x, :o, :n)"
        ),
        {"d": decision, "s": session, "x": variable, "o": old, "n": new},
    )


def update_variable(conn, session, variable, value) -> None:
    conn.execute(
        text(
            "UPDATE nukyro.session_variables SET value = :n, updated_at = now() "
            "WHERE session_id = :s AND variable_id = :x"
        ),
        {"s": session, "x": variable, "n": value},
    )


def insert_event(conn, session, version, rule):
    return conn.execute(
        text(
            "INSERT INTO nukyro.session_events (session_id, scenario_version_id, rule_id) "
            "VALUES (:s, :v, :r) RETURNING id"
        ),
        {"s": session, "v": version, "r": rule},
    ).scalar_one()


def insert_cause(conn, event, session, decision) -> None:
    conn.execute(
        text(
            "INSERT INTO nukyro.session_event_causes "
            "(session_event_id, session_id, session_decision_id) VALUES (:e, :s, :d)"
        ),
        {"e": event, "s": session, "d": decision},
    )


def insert_step(conn, session, version, node, seq) -> None:
    conn.execute(
        text(
            "INSERT INTO nukyro.session_steps (session_id, scenario_version_id, node_id, seq) "
            "VALUES (:s, :v, :n, :q)"
        ),
        {"s": session, "v": version, "n": node, "q": seq},
    )


def move_session(conn, session, node, outcome: bool) -> None:
    conn.execute(
        text(
            "UPDATE nukyro.sessions SET current_node_id = :n, last_activity_at = now(), "
            "outcome_node_id = CASE WHEN :o THEN :n ELSE outcome_node_id END, "
            "outcome_reached_at = CASE WHEN :o THEN now() ELSE outcome_reached_at END "
            "WHERE id = :s"
        ),
        {"s": session, "n": node, "o": outcome},
    )


def session_view(conn, participant, session):
    return (
        conn.execute(
            text(SESSION_SELECT + " WHERE s.id = :s AND s.participant_id = :p"),
            {"s": session, "p": participant},
        )
        .mappings()
        .one_or_none()
    )


def node_options(conn, session):
    return _all(
        conn,
        "SELECT o.key, o.label FROM nukyro.options o JOIN nukyro.sessions s "
        "ON s.current_node_id = o.node_id WHERE s.id = :s ORDER BY o.position, o.key",
        s=session,
    )


def node_reasons(conn, session):
    return _all(
        conn,
        "SELECT r.key, r.label FROM nukyro.justification_reasons r JOIN nukyro.sessions s "
        "ON s.current_node_id = r.node_id JOIN nukyro.decision_points d ON d.node_id = r.node_id "
        "WHERE s.id = :s AND d.requires_justification ORDER BY r.position, r.key",
        s=session,
    )


def session_events(conn, session):
    return _all(
        conn,
        "SELECT t.title, t.body FROM nukyro.session_events e "
        "JOIN nukyro.rules r ON r.id = e.rule_id JOIN nukyro.nodes t ON t.id = r.target_node_id "
        "WHERE e.session_id = :s AND r.rule_type = 'event' ORDER BY e.triggered_at, r.key",
        s=session,
    )
