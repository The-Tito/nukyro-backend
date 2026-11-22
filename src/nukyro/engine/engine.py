"""Motor puro de simulación (ADR-009): sin base de datos, reloj ni azar."""

from dataclasses import replace

from nukyro.engine.conditions import evaluate, is_int
from nukyro.engine.model import (
    Activation,
    AppliedEffect,
    Content,
    Decision,
    DomainError,
    InvalidContent,
    Node,
    Result,
    State,
)


def initial_state(content: Content) -> State:
    intros = [n.key for n in content.nodes.values() if n.kind == "intro"]
    if len(intros) != 1:
        raise InvalidContent("invalid_intro")
    values = {k: v.initial for k, v in content.variables.items()}
    return State(intros[0], (intros[0],), values, ())


def _result(content, state, effects, activations, next_key, replayed) -> Result:
    finished = content.nodes[state.current_node_key].kind == "outcome"
    return Result(state, effects, activations, next_key, replayed, finished)


def _apply_effects(content, values, effects):
    values = dict(values)
    applied = []
    for e in effects:
        var = content.variables.get(e.variable_key)
        if var is None or e.op not in ("add", "set") or not is_int(e.value):
            raise InvalidContent("invalid_effect")
        previous = values[var.key]
        raw = previous + e.value if e.op == "add" else e.value
        new = max(var.min_value, min(var.max_value, raw))
        values[var.key] = new
        applied.append(AppliedEffect(var.key, previous, new))
    return values, tuple(applied)


def _activation(rule, truth_causes, decisions) -> Activation:
    order = [d.node_key for d in decisions]
    causes = tuple(k for k in order if k in truth_causes)
    return Activation(
        rule.key, rule.kind, rule.target_key, causes, rule.relation_type, rule.explanation
    )


def _leave(content, state, node: Node, values, decisions, option_next):
    """Pasos 2 a 4: eventos, transiciones y destino por defecto."""
    path = state.path
    rules = sorted(
        (r for r in content.rules if r.node_key == node.key), key=lambda r: (r.priority, r.key)
    )
    activations = []
    target = None
    for kind in ("event", "transition"):
        for rule in (r for r in rules if r.kind == kind):
            truth, causes = evaluate(rule.condition, values, decisions, path)
            if truth:
                activations.append(_activation(rule, causes, decisions))
                if kind == "transition":
                    target = rule.target_key
                    break
    target = target or option_next or node.default_next_node_key
    if target is None or target not in content.nodes:
        raise InvalidContent("no_next_node")
    return tuple(activations), target


def decide(content, state, node_key, option_key, reason_keys) -> Result:
    # RN-14: si ya hay decisión en ese nodo, se devuelve la confirmada.
    prior = next((d for d in state.decisions if d.node_key == node_key), None)
    if prior is not None:
        return _result(content, state, prior.effects, prior.activations, prior.next_node_key, True)
    node = content.nodes.get(node_key)
    if node is None:
        raise DomainError("unknown_node")
    if node_key != state.current_node_key:
        raise DomainError("node_not_current")
    if node.kind != "decision":
        raise DomainError("not_a_decision")
    option = next((o for o in node.options if o.key == option_key), None)
    if option is None:
        raise DomainError("unknown_option")
    reason_keys = tuple(reason_keys)
    correct = _check_reasons(node, reason_keys)

    values, applied = _apply_effects(content, state.values, option.effects)
    pending = Decision(node_key, option_key, reason_keys, correct, applied, (), None)
    decisions = (*state.decisions, pending)
    activations, target = _leave(content, state, node, values, decisions, option.next_node_key)
    decision = replace(pending, activations=activations, next_node_key=target)
    new_state = State(target, (*state.path, target), values, (*state.decisions, decision))
    return _result(content, new_state, applied, activations, target, False)


def _check_reasons(node: Node, reason_keys) -> bool:
    if not node.requires_justification:
        if reason_keys:
            raise DomainError("reasons_not_allowed")
        return True
    if not reason_keys:
        raise DomainError("reasons_required")
    if len(set(reason_keys)) != len(reason_keys):
        raise DomainError("duplicate_reason")
    by_key = {r.key: r.correct for r in node.reasons}
    if any(k not in by_key for k in reason_keys):
        raise DomainError("unknown_reason")
    hits = sum(by_key[k] for k in reason_keys)
    return hits >= node.min_correct and hits == len(reason_keys)


def advance(content, state, from_node_key) -> Result:
    node = content.nodes.get(from_node_key)
    if node is None:
        raise DomainError("unknown_node")
    if from_node_key != state.current_node_key:
        if from_node_key in state.path:
            return _result(content, state, (), (), state.current_node_key, True)
        raise DomainError("node_not_current")
    if node.kind == "decision":
        raise DomainError("decision_pending")
    if node.kind in ("outcome", "event"):
        raise DomainError("not_advanceable")
    activations, target = _leave(content, state, node, state.values, state.decisions, None)
    new_state = State(target, (*state.path, target), state.values, state.decisions)
    return _result(content, new_state, (), activations, target, False)
