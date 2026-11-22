# ruff: noqa: E501
"""DEMO-BECAS (T-13, D-17): estructura, conteos, RF-066 y los tres recorridos con el motor puro."""

import json
import re
from pathlib import Path

import pytest
from recorridos import RECORRIDOS, VARIABLES

from nukyro.engine.engine import advance, decide, initial_state
from nukyro.engine.validation import validate
from nukyro.modules.simulation.service import _content

SPEC = json.loads((Path(__file__).parents[2] / "demo" / "scenario-becas.json").read_text("utf-8"))
NODES = {n["key"]: n for n in SPEC["nodes"]}
DECISIONS = [n for n in SPEC["nodes"] if n["type"] == "decision"]
SETS = SPEC["question_sets"]
PHASES = {"requirements", "design", "development", "testing", "delivery", "incident_response"}


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


def test_conteos_exactos():
    kinds = [n["type"] for n in SPEC["nodes"]]
    assert (kinds.count("decision"), kinds.count("event"), kinds.count("outcome")) == (8, 2, 3)
    assert kinds.count("intro") == 1 and len(SPEC["variables"]) == 3
    assert all(v["min"] is not None and v["max"] is not None for v in SPEC["variables"])
    assert [r["type"] for r in SPEC["rules"]].count("event") == 2
    assert [r["type"] for r in SPEC["rules"]].count("transition") >= 1
    assert {n["phase"] for n in DECISIONS} == PHASES


def test_cada_decision_tiene_objetivo_partes_retroalimentacion_y_referencia():
    objectives = {o["key"] for o in SPEC["objectives"]}
    refs = {r["key"] for r in SPEC["references"]}
    for n in DECISIONS:
        assert n["objective"] in objectives and n["affected_parties"].strip()
        assert n["feedback"] and all(f["body"].strip() for f in n["feedback"])
        assert n["references"] and set(n["references"]) <= refs
        assert len(n["options"]) >= 2


def test_justificaciones_con_razones_correctas_e_incorrectas():
    justified = [n for n in DECISIONS if n["requires_justification"]]
    assert justified
    for n in justified:
        flags = [r["correct"] for r in n["reasons"]]
        assert flags.count(True) >= n["min_correct"] and False in flags


def test_demostracion_y_referencias_ficticias():
    assert SPEC["key"] == "DEMO-BECAS"
    assert "DEMOSTRACIÓN" in SPEC["title"] and "DEMOSTRACIÓN" in SPEC["introduction"]
    assert {r["category"] for r in SPEC["references"]} == {
        "ethical",
        "professional",
        "normative",
        "legal",
    }
    for r in SPEC["references"]:
        assert "DEMOSTRACIÓN" in r["title"] and "inventad" in r["source"]
        if r["category"] == "legal":
            assert "ficticia" in r["jurisdiction"]
        else:
            assert "no es" in r["source"].lower() and r["jurisdiction"] is None


def test_sin_juicio_moral_ni_nombres_reales():
    text = "\n".join(strings(SPEC)).lower()
    moral = r"\b(bueno|buena|buenos|buenas|malo|mala|malos|malas|inmoral|culpable|irresponsable)\b"
    assert not re.findall(moral, text)
    real = r"(acm|ieee|iso|gdpr|lfpdppp|unam|ipn|méxico|mexico|ley federal|artículo \d)"
    assert not re.findall(r"\b" + real + r"\b", text)


def test_evaluaciones_equivalentes_y_una_sola_correcta():
    assert set(SETS) == {"pretest", "posttest", "transfer", "causal"}
    pre, post = SETS["pretest"], SETS["posttest"]
    assert [(q["topic"], q["objective"], q["assesses"], len(q["options"])) for q in pre] == [
        (q["topic"], q["objective"], q["assesses"], len(q["options"])) for q in post
    ]
    objectives = {o["key"] for o in SPEC["objectives"]}
    for qs in SETS.values():
        for q in qs:
            assert q["topic"] and q["objective"] in objectives and q["prompt"]
            assert sum(o["correct"] for o in q["options"]) == 1
    assert any(q.get("requires") for q in SETS["causal"])
    assert all(NODES[q["requires"]]["type"] == "event" for q in SETS["causal"] if q.get("requires"))


def test_pasa_validate_de_rf_066():
    assert validate(rows()) == []


@pytest.mark.parametrize("outcome", RECORRIDOS)
def test_recorrido_calculado_a_mano_con_el_motor(outcome):
    expected = RECORRIDOS[outcome]
    content = _content(rows())
    state = advance(content, initial_state(content), "intro").state
    seen = []
    for node, option, reasons, values, correct in expected["steps"]:
        result = decide(content, state, node, option, reasons)
        state = result.state
        assert tuple(state.values[k] for k in VARIABLES) == values, node
        assert state.decisions[-1].correct is correct, node
        seen += [(node, a.rule_key, a.kind, a.causes) for a in result.activations]
    assert seen == expected["activations"]
    assert state.current_node_key == outcome and NODES[outcome]["type"] == "outcome"
    assert set(RECORRIDOS) == {n["key"] for n in SPEC["nodes"] if n["type"] == "outcome"}
