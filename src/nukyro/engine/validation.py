"""Validador de RF-066 (ADR-009 «Publicar exige», D-28, RN-10): puro, sin E/S.

Recibe filas ya leídas (diccionarios simples) y devuelve todos los errores, sin excepciones
ante JSON arbitrario. Formas de entrada:
  nodes:         key, node_type, has_point, requires_justification, min_correct, default_next
  variables:     key, initial_value, min_value, max_value
  options:       key, node_key, effects, next_key
  reasons:       key, node_key, is_correct
  rules:         key, node_key, rule_type, condition, target_key
  objectives:    lista de claves
  question_sets: set_type, questions: [{key, correct}] (correct = opciones correctas)
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from nukyro.engine.conditions import is_int
from nukyro.engine.conditions import validate as validate_condition
from nukyro.engine.model import InvalidContent

INT32_MIN, INT32_MAX = -(2**31), 2**31 - 1


@dataclass(frozen=True)
class Issue:
    code: str
    key: str | None = None


def _int32(value: Any) -> bool:
    return is_int(value) and INT32_MIN <= value <= INT32_MAX


def _condition_refs(cond: dict, out: list) -> None:
    """(tipo, clave) de las referencias de una condición ya válida."""
    if "var" in cond:
        out.append(("var", cond["var"]))
        return
    ((name, arg),) = cond.items()
    if name in ("chose", "visited"):
        out.append((name, arg))
    elif name == "not":
        _condition_refs(arg, out)
    else:
        for sub in arg:
            _condition_refs(sub, out)


def _check_condition(rule, variables, options, nodes, issues) -> None:
    try:
        validate_condition(rule["condition"])
    except InvalidContent:
        issues.append(Issue("invalid_condition", rule["key"]))
        return
    refs: list = []
    _condition_refs(rule["condition"], refs)
    known = {"var": variables, "chose": options, "visited": nodes}
    codes = {"var": "unknown_variable", "chose": "unknown_option", "visited": "unknown_node"}
    for kind, key in refs:
        if key not in known[kind]:
            issues.append(Issue(codes[kind], rule["key"]))


def _check_effects(option, variables, issues) -> list[tuple[str, str, int]]:
    """Valida los efectos de una alternativa; devuelve (variable, op, valor) de los válidos."""
    effects = option["effects"]
    if not isinstance(effects, list):
        issues.append(Issue("invalid_effect", option["key"]))
        return []
    good = []
    for e in effects:
        shape = (
            isinstance(e, dict)
            and set(e) == {"variable_key", "op", "value"}
            and isinstance(e["variable_key"], str)
            and isinstance(e["op"], str)
            and e["op"] in ("add", "set")
            and is_int(e["value"])
        )
        if not shape:
            issues.append(Issue("invalid_effect", option["key"]))
        elif e["variable_key"] not in variables:
            issues.append(Issue("unknown_variable", option["key"]))
        elif not _int32(e["value"]):
            issues.append(Issue("int_out_of_range", option["key"]))
        else:
            good.append((e["variable_key"], e["op"], e["value"]))
    return good


def _check_overflow(rows, good_effects, issues) -> None:
    """Una variable sin algún límite no debe poder salirse del integer de la base.

    Cota conservadora: como cada nodo se visita una vez, el valor máximo posible es la mayor
    magnitud inicial o de un `set` más, por cada nodo, la suma de |add| de su peor alternativa.
    """
    for var in rows["variables"]:
        if var["min_value"] is not None and var["max_value"] is not None:
            continue
        key = var["key"]
        bound = abs(var["initial_value"]) if is_int(var["initial_value"]) else 0
        per_node: dict[str, int] = {}
        for opt in rows["options"]:
            mine = good_effects.get(opt["key"], [])
            bound = max([bound] + [abs(v) for k, op, v in mine if k == key and op == "set"])
            adds = sum(abs(v) for k, op, v in mine if k == key and op == "add")
            per_node[opt["node_key"]] = max(per_node.get(opt["node_key"], 0), adds)
        if bound + sum(per_node.values()) > INT32_MAX:
            issues.append(Issue("variable_overflow", key))


def _routes(rows, nodes):
    """Aristas de la ruta, destinos solo mostrados (reglas event) y nodos sin salida de respaldo."""
    options: dict[str, list] = {}
    for o in rows["options"]:
        options.setdefault(o["node_key"], []).append(o)
    route: dict[str, set] = {k: set() for k in nodes}
    shown: dict[str, set] = {k: set() for k in nodes}
    dead: list[str] = []
    for key, n in nodes.items():
        if n["node_type"] == "outcome":
            continue
        if n["node_type"] == "decision":
            fallbacks = [o["next_key"] or n["default_next"] for o in options.get(key, [])]
        else:
            fallbacks = [n["default_next"]]
        for fallback in fallbacks:
            if fallback is None:
                dead.append(key)
            elif fallback in nodes:
                route[key].add(fallback)
    for r in rows["rules"]:
        if r["node_key"] in nodes and r["target_key"] in nodes:
            edges = route if r["rule_type"] == "transition" else shown
            edges[r["node_key"]].add(r["target_key"])
    return route, shown, dead


def _cycles(route) -> list[str]:
    found, state = [], {}
    for start in route:
        if start in state:
            continue
        state[start] = 1
        stack = [(start, iter(sorted(route[start])))]
        while stack:
            node, it = stack[-1]
            for nxt in it:
                if state.get(nxt) == 1:
                    found.append(nxt)
                elif nxt not in state:
                    state[nxt] = 1
                    stack.append((nxt, iter(sorted(route[nxt]))))
                    break
            else:
                state[node] = 2
                stack.pop()
    return found


def validate(rows: Mapping[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    nodes = {n["key"]: n for n in rows["nodes"]}
    variables = {v["key"] for v in rows["variables"]}
    options = {o["key"] for o in rows["options"]}
    by_node: dict[str, list] = {}
    for o in rows["options"]:
        by_node.setdefault(o["node_key"], []).append(o)

    # Destinos: existen; una regla event muestra un evento. La ruta admite los cuatro tipos (RF-015)
    def target(key, dest, event_only):
        if dest is None:
            return
        if dest not in nodes:
            issues.append(Issue("unknown_target", key))
        elif event_only and nodes[dest]["node_type"] != "event":
            issues.append(Issue("wrong_target_type", key))

    for n in nodes.values():
        target(n["key"], n["default_next"], False)
    for o in rows["options"]:
        target(o["key"], o["next_key"], False)
    for r in rows["rules"]:
        target(r["key"], r["target_key"], r["rule_type"] == "event")
        _check_condition(r, variables, options, nodes, issues)

    # Un solo intro, alcance, ciclos y rutas con desenlace
    intros = [k for k, n in nodes.items() if n["node_type"] == "intro"]
    if len(intros) != 1:
        issues.append(Issue("intro_count"))
    route, shown, dead = _routes(rows, nodes)
    if len(intros) == 1:
        walked, todo = {intros[0]}, [intros[0]]
        while todo:
            for nxt in route[todo.pop()] - walked:
                walked.add(nxt)
                todo.append(nxt)
        # Un evento solo mostrado es alcanzable, pero no se sale de él (ADR-009)
        seen = walked.union(*(shown[k] for k in walked))
        issues += [Issue("unreachable_node", k) for k in nodes if k not in seen]
        dead = [k for k in dead if k in walked or nodes[k]["node_type"] != "event"]
    issues += [Issue("cycle", k) for k in _cycles(route)]
    issues += [Issue("route_without_outcome", k) for k in dict.fromkeys(dead)]

    for key, n in nodes.items():
        if n["node_type"] == "decision":
            if not n["has_point"]:
                issues.append(Issue("decision_without_point", key))
            if not by_node.get(key):
                issues.append(Issue("decision_without_option", key))
        if n["node_type"] == "outcome" and (
            n["default_next"]
            or by_node.get(key)
            or any(r["node_key"] == key for r in rows["rules"])
        ):
            issues.append(Issue("outcome_with_exits", key))

    # Variables y efectos
    for v in rows["variables"]:
        ints = [v["initial_value"], v["min_value"], v["max_value"]]
        if not all(x is None or _int32(x) for x in ints):
            issues.append(Issue("int_out_of_range", v["key"]))
        elif (
            v["min_value"] is not None
            and v["max_value"] is not None
            and v["min_value"] > v["max_value"]
        ):
            issues.append(Issue("invalid_range", v["key"]))
    good = {o["key"]: _check_effects(o, variables, issues) for o in rows["options"]}
    _check_overflow(rows, good, issues)

    # Justificación
    correct: dict[str, int] = {}
    for r in rows["reasons"]:
        correct[r["node_key"]] = correct.get(r["node_key"], 0) + bool(r["is_correct"])
    for key, n in nodes.items():
        if n["has_point"] and n["requires_justification"]:
            if n["min_correct"] < 1:
                issues.append(Issue("invalid_min_correct", key))
            elif correct.get(key, 0) < n["min_correct"]:
                issues.append(Issue("insufficient_correct_reasons", key))

    # Evaluaciones (D-28) y objetivos (RN-10)
    sets = {s["set_type"]: s["questions"] for s in rows["question_sets"]}
    if "pretest" not in sets:
        issues.append(Issue("pretest_missing"))
    elif not sets["pretest"]:
        issues.append(Issue("pretest_empty"))
    for questions in sets.values():
        issues += [
            Issue("question_correct_count", q["key"]) for q in questions if q["correct"] != 1
        ]
    if not rows["objectives"]:
        issues.append(Issue("no_objectives"))
    return list(dict.fromkeys(issues))
