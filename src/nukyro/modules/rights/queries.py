"""Proyección explícita del historial propio y operaciones sobre el titular ya bloqueado."""

from sqlalchemy import Connection, text


def export_data(conn: Connection, participant) -> dict:
    params = {"participant": participant}
    acceptances = conn.execute(
        text(
            "SELECT document_type, document_version, accepted_at "
            "FROM nukyro.document_acceptances WHERE participant_id = :participant "
            "ORDER BY accepted_at, document_type, document_version"
        ),
        params,
    ).mappings()
    preference = conn.execute(
        text("SELECT exclude_from_stats FROM nukyro.participants WHERE id = :participant"),
        params,
    ).scalar_one()
    sessions = conn.execute(
        text("""
            SELECT s.id, sc.key AS scenario_key, v.version_number AS scenario_version,
                   current_node.key AS current_node_key, outcome_node.key AS outcome_node_key,
                   s.started_at, s.pretest_completed_at, s.outcome_reached_at, s.completed_at,
                   s.last_activity_at, s.self_reported_first, s.has_prior_session,
                   s.is_first_session, s.survey_answered,
                   ARRAY(
                       SELECT jsonb_build_object(
                           'node_key', n.key, 'sequence', st.seq, 'entered_at', st.entered_at
                       )
                       FROM nukyro.session_steps st JOIN nukyro.nodes n ON n.id = st.node_id
                       WHERE st.session_id = s.id ORDER BY st.seq
                   ) AS steps,
                   ARRAY(
                       SELECT jsonb_build_object(
                           'node_key', n.key, 'option_key', o.key, 'decided_at', d.decided_at,
                           'justification_correct', d.justification_correct,
                           'reason_keys', ARRAY(
                               SELECT r.key
                               FROM nukyro.session_decision_reasons dr
                               JOIN nukyro.justification_reasons r ON r.id = dr.reason_id
                               WHERE dr.session_decision_id = d.id ORDER BY r.position, r.key
                           )
                       )
                       FROM nukyro.session_decisions d
                       JOIN nukyro.nodes n ON n.id = d.node_id
                       JOIN nukyro.options o ON o.id = d.option_id
                       WHERE d.session_id = s.id ORDER BY d.decided_at, n.key
                   ) AS decisions,
                   ARRAY(
                       SELECT jsonb_build_object(
                           'kind', qs.set_type, 'started_at', a.started_at,
                           'submitted_at', a.submitted_at, 'score', a.score,
                           'answered_count', a.answered_count, 'correct_count', a.correct_count,
                           'answers', ARRAY(
                               SELECT jsonb_build_object(
                                   'question_key', q.key, 'option_key', qo.key,
                                   'answered_at', aa.answered_at
                               )
                               FROM nukyro.assessment_answers aa
                               JOIN nukyro.questions q ON q.id = aa.question_id
                               JOIN nukyro.question_options qo ON qo.id = aa.option_id
                               WHERE aa.attempt_id = a.id ORDER BY q.position, q.key
                           )
                       )
                       FROM nukyro.assessment_attempts a
                       JOIN nukyro.question_sets qs ON qs.id = a.question_set_id
                       WHERE a.session_id = s.id ORDER BY a.started_at, qs.set_type
                   ) AS assessments,
                   ARRAY(
                       SELECT jsonb_build_object(
                           'rule_key', r.key, 'triggered_at', e.triggered_at,
                           'decision_node_keys', ARRAY(
                               SELECT n.key FROM nukyro.session_event_causes c
                               JOIN nukyro.session_decisions d ON d.id = c.session_decision_id
                               JOIN nukyro.nodes n ON n.id = d.node_id
                               WHERE c.session_event_id = e.id ORDER BY d.decided_at, n.key
                           )
                       )
                       FROM nukyro.session_events e JOIN nukyro.rules r ON r.id = e.rule_id
                       WHERE e.session_id = s.id ORDER BY e.triggered_at, r.key
                   ) AS events
              FROM nukyro.sessions s
              JOIN nukyro.scenario_versions v ON v.id = s.scenario_version_id
              JOIN nukyro.scenarios sc ON sc.id = v.scenario_id
              JOIN nukyro.nodes current_node ON current_node.id = s.current_node_id
              LEFT JOIN nukyro.nodes outcome_node ON outcome_node.id = s.outcome_node_id
             WHERE s.participant_id = :participant
             ORDER BY s.started_at, s.id
        """),
        params,
    ).mappings()
    return {
        "exclude_from_stats": preference,
        "acceptances": [dict(row) for row in acceptances],
        "sessions": [dict(row) for row in sessions],
    }


def erase_data(conn: Connection, participant) -> None:
    conn.execute(
        text("SELECT nukyro.erase_anonymous_participant(:participant)"),
        {"participant": participant},
    )


def oppose_statistics(conn: Connection, participant) -> None:
    conn.execute(
        text(
            "UPDATE nukyro.participants SET exclude_from_stats = true "
            "WHERE id = :participant AND NOT exclude_from_stats"
        ),
        {"participant": participant},
    )
