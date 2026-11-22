# ruff: noqa: E501
"""Carga de demo/scenario-becas.json y su forma como filas de la base (compartido por las pruebas de T-13)."""

import json
from pathlib import Path

SPEC = json.loads((Path(__file__).parents[1] / "demo" / "scenario-becas.json").read_text("utf-8"))
NODES = {n["key"]: n for n in SPEC["nodes"]}
DECISIONS = [n for n in SPEC["nodes"] if n["type"] == "decision"]
SETS = SPEC["question_sets"]


def rows() -> dict:
    """Filas con la forma de la base: sirven al validador (RF-066) y al motor."""
    return {
        "nodes": [
            {
                "key": n["key"], "node_type": n["type"], "has_point": n["type"] == "decision",
                "requires_justification": n.get("requires_justification", False),
                "min_correct": n.get("min_correct", 1), "default_next": n.get("next"),
            }
            for n in SPEC["nodes"]
        ],
        "variables": [
            {"key": v["key"], "initial_value": v["initial"], "min_value": v["min"], "max_value": v["max"]}
            for v in SPEC["variables"]
        ],
        "options": [
            {"key": o["key"], "node_key": n["key"], "effects": o["effects"], "next_key": o.get("next")}
            for n in DECISIONS for o in n["options"]
        ],
        "reasons": [
            {"key": r["key"], "node_key": n["key"], "is_correct": r["correct"]}
            for n in DECISIONS for r in n.get("reasons", [])
        ],
        "rules": [
            {
                "key": r["key"], "node_key": r["from"], "rule_type": r["type"], "condition": r["condition"],
                "target_key": r["target"], "priority": r["priority"], "relation_type": r["relation"],
                "explanation": r["explanation"],
            }
            for r in SPEC["rules"]
        ],
        "objectives": [o["key"] for o in SPEC["objectives"]],
        "question_sets": [
            {"set_type": t, "questions": [
                {"key": q["key"], "correct": sum(o["correct"] for o in q["options"])} for q in qs
            ]}
            for t, qs in SETS.items()
        ],
    }  # fmt: skip


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)
