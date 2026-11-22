"""Gramática y evaluación de condiciones con cálculo de causas (ADR-009)."""

import operator
from collections.abc import Sequence
from typing import Any

from nukyro.engine.model import Decision, InvalidContent

MAX_DEPTH = 8
_OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "lte": operator.le,
    "gt": operator.gt,
    "gte": operator.ge,
}


def is_int(value: Any) -> bool:
    """Un booleano no es un entero."""
    return isinstance(value, int) and not isinstance(value, bool)


def _invalid() -> InvalidContent:
    return InvalidContent("invalid_condition")


def validate(cond: Any, depth: int = 1) -> None:
    if depth > MAX_DEPTH or not isinstance(cond, dict):
        raise _invalid()
    if "var" in cond:
        ok = set(cond) == {"var", "op", "value"}
        if not (
            ok and isinstance(cond["var"], str) and cond["op"] in _OPS and is_int(cond["value"])
        ):
            raise _invalid()
        return
    if len(cond) != 1:
        raise _invalid()
    ((name, arg),) = cond.items()
    if name in ("chose", "visited"):
        if not isinstance(arg, str):
            raise _invalid()
    elif name in ("all", "any"):
        if not isinstance(arg, list) or not arg:
            raise _invalid()
        for sub in arg:
            validate(sub, depth + 1)
    elif name == "not":
        validate(arg, depth + 1)
    else:
        raise _invalid()


def _mentioned(cond: dict) -> set[str]:
    """Variables que menciona una condición."""
    if "var" in cond:
        return {cond["var"]}
    ((name, arg),) = cond.items()
    if name == "not":
        return _mentioned(arg)
    if name in ("all", "any"):
        return set().union(*(_mentioned(c) for c in arg))
    return set()


def _changed(decisions: Sequence[Decision], variables: set[str]) -> frozenset[str]:
    return frozenset(
        d.node_key
        for d in decisions
        for e in d.effects
        if e.variable_key in variables and e.previous != e.new
    )


def evaluate(
    cond: Any,
    values: dict[str, int],
    decisions: Sequence[Decision],
    path: Sequence[str],
) -> tuple[bool, frozenset[str]]:
    """Devuelve (verdadera, nodos de las decisiones causantes). Sin causas si es falsa."""
    validate(cond)
    return _eval(cond, values, decisions, path)


def _eval(cond, values, decisions, path):
    if "var" in cond:
        current = values.get(cond["var"])
        if current is None or not _OPS[cond["op"]](current, cond["value"]):
            return False, frozenset()
        return True, _changed(decisions, {cond["var"]})
    ((name, arg),) = cond.items()
    if name == "chose":
        hit = frozenset(d.node_key for d in decisions if d.option_key == arg)
        return bool(hit), hit
    if name == "visited":
        return arg in path, frozenset()
    if name == "not":
        truth, _ = _eval(arg, values, decisions, path)
        return (False, frozenset()) if truth else (True, _changed(decisions, _mentioned(arg)))
    parts = [_eval(c, values, decisions, path) for c in arg]
    if name == "all":
        if not all(t for t, _ in parts):
            return False, frozenset()
    elif not any(t for t, _ in parts):
        return False, frozenset()
    return True, frozenset().union(*(c for t, c in parts if t))
