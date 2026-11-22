"""SQL explícito de la publicación (P12). Solo lo que permite el rol admin."""

from sqlalchemy import Connection, text


def version_scenario(conn: Connection, version):
    """Escenario de la versión. No cambia nunca (trigger), así que se lee sin bloqueo."""
    return conn.execute(
        text("SELECT scenario_id FROM nukyro.scenario_versions WHERE id = :v"), {"v": version}
    ).scalar_one_or_none()


def lock_scenario(conn: Connection, scenario) -> None:
    conn.execute(text("SELECT id FROM nukyro.scenarios WHERE id = :s FOR UPDATE"), {"s": scenario})


def lock_version(conn: Connection, version) -> str | None:
    """Estado de la versión, con bloqueo exclusivo: la edición (FOR SHARE) espera."""
    return conn.execute(
        text("SELECT status FROM nukyro.scenario_versions WHERE id = :v FOR UPDATE"),
        {"v": version},
    ).scalar_one_or_none()


def admin_is_active(conn: Connection, admin) -> bool:
    return bool(
        conn.execute(
            text("SELECT is_active FROM nukyro.admin_users WHERE id = :a FOR SHARE"), {"a": admin}
        ).scalar_one_or_none()
    )


def _all(conn, sql, version):
    return [dict(r) for r in conn.execute(text(sql), {"v": version}).mappings()]


def load_rows(conn: Connection, version) -> dict:
    """Contenido de la versión en la forma que valida `engine.validation.validate`."""
    sets: dict[str, list] = {}
    for r in _all(
        conn,
        "SELECT s.set_type, q.key, count(o.id) FILTER (WHERE o.is_correct) AS correct "
        "FROM nukyro.question_sets s LEFT JOIN nukyro.questions q ON q.question_set_id = s.id "
        "LEFT JOIN nukyro.question_options o ON o.question_id = q.id "
        "WHERE s.version_id = :v GROUP BY s.set_type, q.id, q.key ORDER BY s.set_type, q.key",
        version,
    ):
        questions = sets.setdefault(r["set_type"], [])
        if r["key"] is not None:
            questions.append({"key": r["key"], "correct": r["correct"]})
    return {
        "nodes": _all(
            conn,
            "SELECT n.key, n.node_type, (d.node_id IS NOT NULL) AS has_point, "
            "coalesce(d.requires_justification, false) AS requires_justification, "
            "coalesce(d.min_correct_reasons, 1)::int AS min_correct, dn.key AS default_next "
            "FROM nukyro.nodes n LEFT JOIN nukyro.decision_points d ON d.node_id = n.id "
            "LEFT JOIN nukyro.nodes dn ON dn.id = n.default_next_node_id "
            "WHERE n.version_id = :v ORDER BY n.key",
            version,
        ),
        "variables": _all(
            conn,
            "SELECT key, initial_value, min_value, max_value FROM nukyro.state_variables "
            "WHERE version_id = :v ORDER BY key",
            version,
        ),
        "options": _all(
            conn,
            "SELECT o.key, n.key AS node_key, o.effects, nx.key AS next_key "
            "FROM nukyro.options o JOIN nukyro.nodes n ON n.id = o.node_id "
            "LEFT JOIN nukyro.nodes nx ON nx.id = o.next_node_id "
            "WHERE o.version_id = :v ORDER BY o.key",
            version,
        ),
        "reasons": _all(
            conn,
            "SELECT r.key, n.key AS node_key, r.is_correct FROM nukyro.justification_reasons r "
            "JOIN nukyro.nodes n ON n.id = r.node_id WHERE r.version_id = :v ORDER BY r.key",
            version,
        ),
        "rules": _all(
            conn,
            "SELECT r.key, f.key AS node_key, r.rule_type, r.condition, t.key AS target_key "
            "FROM nukyro.rules r JOIN nukyro.nodes f ON f.id = r.from_node_id "
            "JOIN nukyro.nodes t ON t.id = r.target_node_id WHERE r.version_id = :v ORDER BY r.key",
            version,
        ),
        "objectives": [
            r["key"]
            for r in _all(
                conn,
                "SELECT key FROM nukyro.learning_objectives WHERE version_id = :v ORDER BY key",
                version,
            )
        ],
        "question_sets": [{"set_type": t, "questions": q} for t, q in sorted(sets.items())],
    }


def retire_published(conn: Connection, scenario) -> None:
    conn.execute(
        text(
            "UPDATE nukyro.scenario_versions SET status = 'retired', retired_at = now() "
            "WHERE scenario_id = :s AND status = 'published'"
        ),
        {"s": scenario},
    )


def publish_draft(conn: Connection, version, admin) -> None:
    conn.execute(
        text(
            "UPDATE nukyro.scenario_versions SET status = 'published', published_at = now(), "
            "published_by = :a WHERE id = :v AND status = 'draft'"
        ),
        {"v": version, "a": admin},
    )
