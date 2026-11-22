"""Importador mínimo: JSON por claves -> borrador, y siembra del escenario de demostración (D-17).

Corre con el rol admin. La siembra no escribe en `published`: solo deja el borrador y llama a
`publish` (P12), que valida RF-066 y D-28. El administrador técnico queda inactivo al terminar.
"""

import json
from datetime import date
from uuid import uuid4

from sqlalchemy import Connection, Engine, text

from nukyro.modules.publishing.service import publish

SEED_SUB = "seed-demo"  # administrador técnico de la siembra (sin datos personales)


class SeedFailed(Exception):
    """Una siembra anterior falló y dejó su borrador: no se da por hecha ni se rehace sola."""


JSON_COLUMNS = {"effects", "condition"}


def _insert(conn: Connection, table: str, **cols) -> None:
    values = {k: json.dumps(v) if k in JSON_COLUMNS else v for k, v in cols.items()}
    marks = ", ".join(f"CAST(:{k} AS jsonb)" if k in JSON_COLUMNS else f":{k}" for k in cols)
    conn.execute(text(f"INSERT INTO nukyro.{table} ({', '.join(cols)}) VALUES ({marks})"), values)


def _day(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _version(conn: Connection, spec: dict, admin) -> tuple:
    """Escenario (se crea si falta) y un borrador nuevo. No borra: RN-16 rechaza un segundo."""
    scenario = conn.execute(
        text("SELECT id FROM nukyro.scenarios WHERE key = :k"), {"k": spec["key"]}
    ).scalar_one_or_none()
    if scenario is None:
        scenario = uuid4()
        _insert(conn, "scenarios", id=scenario, key=spec["key"], title=spec["title"])
    number = conn.execute(
        text(
            "SELECT coalesce(max(version_number), 0) + 1 FROM nukyro.scenario_versions "
            "WHERE scenario_id = :s"
        ),
        {"s": scenario},
    ).scalar_one()
    version = uuid4()
    _insert(
        conn,
        "scenario_versions",
        id=version,
        scenario_id=scenario,
        version_number=number,
        title=spec["title"],
        introduction=spec["introduction"],
        created_by=admin,
    )
    return version


def import_draft(engine: Engine, spec: dict, admin) -> object:
    """Crea el borrador del escenario descrito por `spec`. Una transacción; devuelve la versión."""
    with engine.begin() as conn:
        v = _version(conn, spec, admin)
        ids = {
            "objective": {o["key"]: uuid4() for o in spec["objectives"]},
            "node": {n["key"]: uuid4() for n in spec["nodes"]},
            "reference": {r["key"]: uuid4() for r in spec["references"]},
        }
        for i, o in enumerate(spec["objectives"]):
            _insert(
                conn,
                "learning_objectives",
                id=ids["objective"][o["key"]],
                version_id=v,
                key=o["key"],
                description=o["description"],
                position=i,
            )
        for x in spec["variables"]:
            _insert(
                conn,
                "state_variables",
                version_id=v,
                key=x["key"],
                label=x["label"],
                initial_value=x["initial"],
                min_value=x.get("min"),
                max_value=x.get("max"),
            )
        for r in spec["references"]:
            _insert(
                conn,
                "educational_references",
                id=ids["reference"][r["key"]],
                version_id=v,
                key=r["key"],
                ref_category=r["category"],
                title=r["title"],
                source=r["source"],
                section=r.get("section"),
                version_label=r.get("version_label"),
                jurisdiction=r.get("jurisdiction"),
                consulted_on=_day(r.get("consulted_on")),
                valid_from=_day(r.get("valid_from")),
            )
        for i, n in enumerate(spec["nodes"]):
            _insert(
                conn,
                "nodes",
                id=ids["node"][n["key"]],
                version_id=v,
                key=n["key"],
                node_type=n["type"],
                title=n["title"],
                body=n["body"],
                project_phase=n.get("phase"),
                position=i,
                default_next_node_id=ids["node"][n["next"]] if n.get("next") else None,
            )
        for n in spec["nodes"]:
            if n["type"] == "decision":
                _decision(conn, v, ids, n)
        for r in spec["rules"]:
            _insert(
                conn,
                "rules",
                version_id=v,
                key=r["key"],
                rule_type=r["type"],
                from_node_id=ids["node"][r["from"]],
                condition=r["condition"],
                target_node_id=ids["node"][r["target"]],
                relation_type=r["relation"],
                priority=r["priority"],
                explanation=r["explanation"],
            )
        for set_type, questions in spec["question_sets"].items():
            _questions(conn, v, ids, set_type, questions)
    return v


def _decision(conn: Connection, v, ids: dict, n: dict) -> None:
    node = ids["node"][n["key"]]
    _insert(
        conn,
        "decision_points",
        node_id=node,
        version_id=v,
        requires_justification=n["requires_justification"],
        evaluated_for_h05=n.get("h05", False),
        min_correct_reasons=n.get("min_correct", 1),
        learning_objective_id=ids["objective"][n["objective"]],
        affected_parties=n["affected_parties"],
    )
    for ref in n["references"]:
        _insert(
            conn,
            "decision_references",
            version_id=v,
            node_id=node,
            reference_id=ids["reference"][ref],
        )
    for i, f in enumerate(n["feedback"]):
        _insert(
            conn,
            "feedback_items",
            version_id=v,
            node_id=node,
            category=f["category"],
            body=f["body"],
            position=i,
        )
    for i, o in enumerate(n["options"]):
        _insert(
            conn,
            "options",
            version_id=v,
            node_id=node,
            key=o["key"],
            label=o["label"],
            effects=o["effects"],
            position=i,
            next_node_id=ids["node"][o["next"]] if o.get("next") else None,
        )
    for i, r in enumerate(n.get("reasons", [])):
        _insert(
            conn,
            "justification_reasons",
            version_id=v,
            node_id=node,
            key=r["key"],
            label=r["label"],
            is_correct=r["correct"],
            position=i,
        )


def _questions(conn: Connection, v, ids: dict, set_type: str, questions: list) -> None:
    qset = uuid4()
    _insert(conn, "question_sets", id=qset, version_id=v, set_type=set_type)
    for i, q in enumerate(questions):
        qid = uuid4()
        assesses = ids["node"][q["assesses"]] if q.get("assesses") else None
        requires = ids["node"][q["requires"]] if q.get("requires") else None
        _insert(
            conn,
            "questions",
            id=qid,
            version_id=v,
            question_set_id=qset,
            key=q["key"],
            prompt=q["prompt"],
            topic=q["topic"],
            position=i,
            learning_objective_id=ids["objective"][q["objective"]],
            assesses_decision_node_id=assesses,
            requires_node_id=requires,
        )
        for j, o in enumerate(q["options"]):
            _insert(
                conn,
                "question_options",
                version_id=v,
                question_id=qid,
                key=o["key"],
                label=o["label"],
                is_correct=o["correct"],
                position=j,
            )


def _set_admin_active(engine: Engine, active: bool):
    with engine.begin() as conn:
        return conn.execute(
            text(
                "INSERT INTO nukyro.admin_users (cognito_sub, email, display_name, is_active) "
                "VALUES (:sub, 'seed-demo@example.test', 'Siembra de demostración', :a) "
                "ON CONFLICT (cognito_sub) DO UPDATE SET is_active = :a RETURNING id"
            ),
            {"sub": SEED_SUB, "a": active},
        ).scalar_one()


def seed_demo(engine: Engine, spec: dict) -> bool:
    """Siembra y publica el escenario si no existe. Nunca toca uno existente.

    Corre en cada arranque de Compose: un borrador o un retiro de un administrador se respeta.
    Si el escenario solo tiene borradores de la propia siembra, es que una siembra anterior falló
    al publicar: se avisa con `SeedFailed` y no se borra ni se revierte nada.
    """
    with engine.connect() as conn:
        versions = conn.execute(
            text(
                "SELECT v.status, coalesce(a.cognito_sub = :sub, false) AS own "
                "FROM nukyro.scenarios s JOIN nukyro.scenario_versions v ON v.scenario_id = s.id "
                "LEFT JOIN nukyro.admin_users a ON a.id = v.created_by WHERE s.key = :k"
            ),
            {"k": spec["key"], "sub": SEED_SUB},
        ).all()
    if versions:
        if all(status == "draft" and own for status, own in versions):
            raise SeedFailed(
                f"{spec['key']}: una siembra anterior falló y dejó su borrador sin publicar. "
                "No se borra ni se publica solo: revisa ese borrador, que creó la propia siembra, "
                "antes de volver a sembrar."
            )
        return False
    admin = _set_admin_active(engine, True)
    try:
        publish(engine, import_draft(engine, spec, admin), admin)
    finally:
        _set_admin_active(engine, False)
    return True
