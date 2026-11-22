"""SQL explícito del resumen (T-15). Solo lectura: sin opciones no elegidas ni correctas."""

from sqlalchemy import Connection, text


def _all(conn, sql, **params):
    return conn.execute(text(sql), params).mappings().all()


def decisions(conn: Connection, session):
    """Historial en el orden del recorrido, con la alternativa elegida."""
    return _all(
        conn,
        "SELECT d.id, d.node_id, d.option_id, n.key, n.title, o.key AS option_key, "
        "o.label AS option_label, d.decided_at FROM nukyro.session_decisions d "
        "JOIN nukyro.nodes n ON n.id = d.node_id JOIN nukyro.options o ON o.id = d.option_id "
        "JOIN nukyro.session_steps st ON st.session_id = d.session_id AND st.node_id = d.node_id "
        "WHERE d.session_id = :s ORDER BY st.seq",
        s=session,
    )


def chosen_reasons(conn: Connection, session):
    """Solo las razones elegidas; is_correct no se lee."""
    return _all(
        conn,
        "SELECT r.session_decision_id, jr.key, jr.label FROM nukyro.session_decision_reasons r "
        "JOIN nukyro.session_decisions d ON d.id = r.session_decision_id "
        "JOIN nukyro.justification_reasons jr ON jr.id = r.reason_id "
        "WHERE d.session_id = :s ORDER BY jr.position, jr.key",
        s=session,
    )


def events(conn: Connection, session):
    """Consecuencias: eventos y transiciones guardados, sin valores de variables."""
    return _all(
        conn,
        "SELECT e.id, r.rule_type, r.relation_type, r.explanation, tn.key, tn.title "
        "FROM nukyro.session_events e JOIN nukyro.rules r ON r.id = e.rule_id "
        "JOIN nukyro.nodes tn ON tn.id = r.target_node_id "
        "WHERE e.session_id = :s ORDER BY e.triggered_at, r.key",
        s=session,
    )


def causes(conn: Connection, session):
    return _all(
        conn,
        "SELECT c.session_event_id, n.key, n.title FROM nukyro.session_event_causes c "
        "JOIN nukyro.session_decisions d ON d.id = c.session_decision_id "
        "JOIN nukyro.nodes n ON n.id = d.node_id "
        "JOIN nukyro.session_steps st ON st.session_id = d.session_id AND st.node_id = d.node_id "
        "WHERE c.session_id = :s ORDER BY st.seq",
        s=session,
    )


def feedback(conn: Connection, session):
    """Retroalimentación general de la decisión y la de SU alternativa; no la de las demás."""
    return _all(
        conn,
        "SELECT d.id AS decision_id, f.category, f.body, (f.option_id IS NULL) AS general "
        "FROM nukyro.session_decisions d JOIN nukyro.feedback_items f "
        "ON f.node_id = d.node_id AND (f.option_id IS NULL OR f.option_id = d.option_id) "
        "WHERE d.session_id = :s ORDER BY f.option_id IS NOT NULL, f.position, f.id",
        s=session,
    )


def references(conn: Connection, session):
    return _all(
        conn,
        "SELECT d.id AS decision_id, er.ref_category, er.title, er.source, er.url, er.section, "
        "er.version_label, er.jurisdiction, er.valid_from FROM nukyro.session_decisions d "
        "JOIN nukyro.decision_references dr ON dr.node_id = d.node_id "
        "JOIN nukyro.educational_references er ON er.id = dr.reference_id "
        "WHERE d.session_id = :s ORDER BY er.key",
        s=session,
    )


def results(conn: Connection, session):
    """Agregados por evaluación enviada: puntuación, aciertos y total."""
    return _all(
        conn,
        "SELECT st.set_type, a.score, a.correct_count, a.answered_count "
        "FROM nukyro.assessment_attempts a "
        "JOIN nukyro.question_sets st ON st.id = a.question_set_id "
        "WHERE a.session_id = :s AND a.submitted_at IS NOT NULL",
        s=session,
    )


def justifications(conn: Connection, session):
    """Aciertos y total de las decisiones evaluadas (H05) y la rúbrica fijada en la versión."""
    return (
        conn.execute(
            text(
                "SELECT count(*) FILTER (WHERE d.justification_correct) AS correct, "
                "count(*) AS total, min(v.rubric_version) AS rubric_version "
                "FROM nukyro.session_decisions d "
                "JOIN nukyro.decision_points dp "
                "ON dp.node_id = d.node_id AND dp.evaluated_for_h05 "
                "JOIN nukyro.scenario_versions v ON v.id = d.scenario_version_id "
                "WHERE d.session_id = :s"
            ),
            {"s": session},
        )
        .mappings()
        .one()
    )
