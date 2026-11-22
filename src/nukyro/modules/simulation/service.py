"""Reglas de la simulación (P5): una transacción por operación, el motor decide (ADR-009)."""

from types import MappingProxyType
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Engine

from nukyro.engine import engine as motor
from nukyro.engine.model import (
    Activation,
    AppliedEffect,
    Content,
    Decision,
    DomainError,
    Effect,
    InvalidContent,
    Node,
    Option,
    Reason,
    Rule,
    State,
    Variable,
)
from nukyro.modules.entry import queries as entry_queries
from nukyro.modules.entry import service as entry_service
from nukyro.modules.simulation import queries
from nukyro.security import hash_secret

# Entrada inválida (422); cualquier otro error del dominio es de estado (409).
INVALID_INPUT = {
    "unknown_node",
    "unknown_option",
    "unknown_reason",
    "reasons_required",
    "reasons_not_allowed",
    "duplicate_reason",
}
KIND = {"info": "narrative"}


def _content(rows: dict) -> Content:
    options: dict[str, list] = {}
    for o in rows["options"]:
        try:
            effects = tuple(Effect(e["variable_key"], e["op"], e["value"]) for e in o["effects"])
        except (KeyError, TypeError):
            raise InvalidContent("invalid_effect") from None
        options.setdefault(o["node_key"], []).append(Option(o["key"], effects, o["next_key"]))
    reasons: dict[str, list] = {}
    for r in rows["reasons"]:
        reasons.setdefault(r["node_key"], []).append(Reason(r["key"], r["is_correct"]))
    nodes = {
        n["key"]: Node(
            n["key"],
            KIND.get(n["node_type"], n["node_type"]),
            tuple(options.get(n["key"], ())),
            tuple(reasons.get(n["key"], ())),
            bool(n["requires_justification"]),
            n["min_correct"],
            n["default_next"],
        )
        for n in rows["nodes"]
    }
    variables = {
        v["key"]: Variable(v["key"], v["initial_value"], v["min_value"], v["max_value"])
        for v in rows["variables"]
    }
    rules = tuple(
        Rule(
            r["key"],
            r["node_key"],
            r["rule_type"],
            r["priority"],
            r["condition"],
            r["target_key"],
            r["relation_type"],
            r["explanation"],
        )
        for r in rows["rules"]
    )
    return Content(nodes, variables, rules)


def _state(rows: dict, content: Content) -> State:
    path = tuple(p["key"] for p in rows["path"])
    reasons: dict = {}
    for r in rows["decision_reasons"]:
        reasons.setdefault(r["decision"], []).append(r["key"])
    effects: dict = {}
    for e in rows["effects"]:
        effects.setdefault(e["decision"], []).append(
            AppliedEffect(e["key"], e["old_value"], e["new_value"])
        )
    causes: dict = {}
    for c in rows["causes"]:
        causes.setdefault(c["event"], set()).add(c["node_key"])
    rules = {r.key: r for r in content.rules}
    order = {k: i for i, k in enumerate(path)}
    activations: dict[str, list] = {}  # por nodo del que se salió
    for e in rows["events"]:
        rule = rules[e["rule_key"]]
        cause_keys = tuple(sorted(causes.get(e["id"], ()), key=lambda k: order.get(k, 0)))
        activations.setdefault(rule.node_key, []).append(
            Activation(
                rule.key,
                rule.kind,
                rule.target_key,
                cause_keys,
                rule.relation_type,
                rule.explanation,
            )
        )
    decisions = []
    for d in rows["decisions"]:
        i = order.get(d["node_key"], -1)
        nxt = path[i + 1] if 0 <= i + 1 < len(path) else None
        decisions.append(
            Decision(
                d["node_key"],
                d["option_key"],
                tuple(reasons.get(d["id"], ())),
                d["justification_correct"],
                tuple(effects.get(d["id"], ())),
                tuple(activations.get(d["node_key"], ())),
                nxt,
            )
        )
    values = MappingProxyType({v["key"]: v["value"] for v in rows["values"]})
    return State(path[-1], path, values, tuple(decisions))


def _ids(rows: dict) -> dict:
    return {
        name: {r["key"]: r["id"] for r in rows[name]}
        for name in ("nodes", "variables", "options", "reasons", "rules")
    }


def _persist(conn, session, version, ids, old_decisions, result) -> None:
    """Escribe solo lo nuevo del resultado. Un reintento no escribe nada."""
    if result.replayed:
        return
    decision_ids = dict(old_decisions)  # nodo -> id de la decisión
    if len(result.state.decisions) > len(old_decisions):
        d = result.state.decisions[-1]
        node = ids["nodes"][d.node_key]
        decision = queries.insert_decision(
            conn, session, version, node, ids["options"][d.option_key], d.correct
        )
        decision_ids[d.node_key] = decision
        for key in d.reason_keys:
            queries.insert_decision_reason(conn, decision, node, ids["reasons"][key])
        for e in d.effects:
            variable = ids["variables"][e.variable_key]
            queries.insert_effect(conn, decision, session, variable, e.previous, e.new)
            queries.update_variable(conn, session, variable, e.new)
    for a in result.activations:
        event = queries.insert_event(conn, session, version, ids["rules"][a.rule_key])
        for cause in a.causes:
            queries.insert_cause(conn, event, session, decision_ids[cause])
    target = result.state.current_node_key
    queries.insert_step(conn, session, version, ids["nodes"][target], len(result.state.path))
    queries.move_session(conn, session, ids["nodes"][target], result.finished)


def _view(conn, participant, session) -> dict:
    row = entry_service._view(queries.session_view(conn, participant, session))
    decision = row["current_node"]["type"] == "decision"
    return {
        **row,
        "options": [dict(r) for r in queries.node_options(conn, session)] if decision else [],
        "reasons": [dict(r) for r in queries.node_reasons(conn, session)] if decision else [],
        "events": [dict(r) for r in queries.session_events(conn, session)],
    }


def _run(engine: Engine, secret: str, session_id: str, act):
    try:
        session = UUID(session_id)
    except ValueError:
        raise HTTPException(404) from None
    try:
        with engine.begin() as conn:
            # El UPDATE bloquea al participante antes que la sesión y renueva su actividad (RF-080)
            participant = entry_queries.touch_participant(conn, hash_secret(secret))
            if participant is None:
                raise HTTPException(401)
            row = queries.lock_session(conn, participant, session)
            if row is None:
                raise HTTPException(404)
            version = row["version"]
            rows = queries.content_rows(conn, version)
            content = _content(rows)
            state_rows = queries.state_rows(conn, session)
            state = _state(state_rows, content)
            ids = _ids(rows)
            current = next(n["key"] for n in rows["nodes"] if n["id"] == row["current_node_id"])
            if current != state.current_node_key:
                raise RuntimeError("el último paso y el nodo actual de la sesión no coinciden")
            pretest_pending = row["pretest_completed_at"] is None and queries.has_pretest(
                conn, version
            )
            result = act(content, state, current == state.path[0] and pretest_pending)
            if result.finished and not result.replayed and row["pretest_completed_at"] is None:
                # El CHECK de la base exige la fecha del pre-test; no se inventa.
                raise DomainError("pretest_pending")
            old = {d["node_key"]: d["id"] for d in state_rows["decisions"]}
            _persist(conn, session, version, ids, old, result)
            return _view(conn, participant, session), result
    except DomainError as exc:
        raise HTTPException(422 if exc.code in INVALID_INPUT else 409) from None


def decide(engine: Engine, secret: str, session_id: str, body) -> dict:
    def act(content, state, gate):
        # Primero el reintento (defecto 1, RN-14): el motor busca antes de validar el nodo.
        if gate and body.node_key == state.current_node_key:
            raise DomainError("pretest_pending")
        return motor.decide(content, state, body.node_key, body.option_key, body.reason_keys)

    view, result = _run(engine, secret, session_id, act)
    d = next(d for d in result.state.decisions if d.node_key == body.node_key)
    return {
        "replayed": result.replayed,
        "confirmed": {
            "node_key": d.node_key,
            "option_key": d.option_key,
            "reason_keys": list(d.reason_keys),
        },
        "session": view,
    }


def advance(engine: Engine, secret: str, session_id: str, body) -> dict:
    def act(content, state, gate):
        if gate and body.from_node_key == state.current_node_key:
            raise DomainError("pretest_pending")
        return motor.advance(content, state, body.from_node_key)

    return _run(engine, secret, session_id, act)[0]


def get_session(engine: Engine, secret: str, session_id: str) -> dict:
    try:
        session = UUID(session_id)
    except ValueError:
        raise HTTPException(404) from None
    with engine.begin() as conn:
        participant = entry_queries.touch_participant(conn, hash_secret(secret))
        if participant is None:
            raise HTTPException(401)
        if queries.session_view(conn, participant, session) is None:
            raise HTTPException(404)
        return _view(conn, participant, session)
