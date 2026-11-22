# ruff: noqa: E501
"""Resumen contra la API y la base reales (T-15, RF-039 a RF-049, RF-056, RF-057, RF-061).

Contenido propio sobre el escenario de test_assessment: D (con justificación) y D2 (sin ella);
D tiene retroalimentación general y de sus dos alternativas (A profesional, B normativa) y una referencia
profesional; D2 tiene una referencia legal con todos sus datos. Se elige A en D: p baja a 1, ocurre el
evento causal EV (regla de D) y la transición de riesgo de D2 hacia OUT_A.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest

from nukyro.modules.assessment.phases import is_abandoned

from .conftest import WRITE
from .test_assessment import at_pretest_done, build, fill, finish, row, start, submit


def enrich(ex, v, n, lo):
    n["D2"] = ex(
        "INSERT INTO nukyro.nodes (version_id, key, node_type, title, body, default_next_node_id) VALUES (%s,'D2','decision','Título D2','Texto D2',%s) RETURNING id",
        (v, n["OUT_A"]),
    ).fetchone()[0]
    ex("UPDATE nukyro.nodes SET default_next_node_id=%s WHERE id=%s", (n["D2"], n["D"]))
    ex(
        "INSERT INTO nukyro.decision_points (node_id, version_id, requires_justification, learning_objective_id, affected_parties) VALUES (%s,%s,false,%s,'x')",
        (n["D2"], v, lo),
    )
    for k in ("A2", "B2"):
        ex(
            "INSERT INTO nukyro.options (version_id, node_id, key, label, effects, next_node_id) VALUES (%s,%s,%s,%s,'[]',NULL)",
            (v, n["D2"], k, f"Alternativa {k}"),
        )
    o = {
        k: i
        for k, i in ex("SELECT key, id FROM nukyro.options WHERE node_id=%s", (n["D"],)).fetchall()
    }
    for opt, cat, body, pos in (
        (None, "ethical", "General de D", 0),
        (o["A"], "professional", "Retro de A", 0),
        (o["B"], "normative", "Retro de B", 0),
    ):
        ex(
            "INSERT INTO nukyro.feedback_items (version_id, node_id, option_id, category, body, position) VALUES (%s,%s,%s,%s,%s,%s)",
            (v, n["D"], opt, cat, body, pos),
        )
    refs = {}
    for k, cat, title, src, url, sec, ver, jur, vf in (
        (
            "REF-PRO",
            "professional",
            "Código profesional",
            "Asociación",
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "REF-LEY",
            "legal",
            "Ley de datos",
            "Diario Oficial",
            "https://example.org/ley",
            "Art. 5",
            "2024-03",
            "México",
            "2020-01-01",
        ),
    ):
        refs[k] = ex(
            "INSERT INTO nukyro.educational_references (version_id, key, ref_category, title, source, url, section, version_label, jurisdiction, valid_from) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (v, k, cat, title, src, url, sec, ver, jur, vf),
        ).fetchone()[0]
    for node, ref in (("D", "REF-PRO"), ("D2", "REF-LEY")):
        ex(
            "INSERT INTO nukyro.decision_references (version_id, node_id, reference_id) VALUES (%s,%s,%s)",
            (v, n[node], refs[ref]),
        )
    ex(
        "INSERT INTO nukyro.rules (version_id, key, rule_type, from_node_id, condition, target_node_id, relation_type, priority, explanation) VALUES (%s,'RULE-TR','transition',%s,%s,%s,'risk',100,'Riesgo de D2')",
        (v, n["D2"], json.dumps({"var": "p", "op": "lt", "value": 2}), n["OUT_A"]),
    )


@pytest.fixture(scope="module")
def rich(superuser):
    return build(superuser, extra=enrich)


@pytest.fixture(scope="module")
def lenient_rich(superuser):
    return build(superuser, lenient=True, extra=enrich)


def play_to_end(client, sid, pre_done=True):
    finish(client, sid, "A", ("R1",))
    body = {"node_key": "D2", "option_key": "A2", "reason_keys": []}
    r = client.post(f"/api/v1/sessions/{sid}/decisions", json=body, headers=WRITE)
    assert r.status_code == 200, r.text
    for kind, picks in (
        ("posttest", {"T1": "c", "T2": "a"}),
        ("transfer", {"X1": "b"}),
        ("causal", {"CE": "a", "CA": "a", "CN": "a"}),
    ):
        fill(client, sid, kind, picks)
        assert submit(client, sid, kind).status_code == 200


def test_rf042_a_rf048_el_resumen_trae_lo_propio_de_cada_decision(person, rich):
    sid = at_pretest_done(person, rich)
    play_to_end(person, sid)
    r = person.get(f"/api/v1/sessions/{sid}/summary")
    assert r.status_code == 200, r.text
    body = r.json()
    d, d2 = body["decisions"]
    assert (d["node_key"], d["option_key"], [x["key"] for x in d["reasons"]]) == ("D", "A", ["R1"])
    # solo la general y la de la alternativa elegida (A, profesional); la de B no sale
    assert [(f["scope"], f["category"], f["body"]) for f in d["feedback"]] == [
        ("decision", "ethical", "General de D"),
        ("option", "professional", "Retro de A"),
    ]
    assert d2["node_key"] == "D2" and d2["feedback"] == []
    # referencias por decisión, sin herencia
    assert d["references"] == [
        {
            "category": "professional",
            "title": "Código profesional",
            "source": "Asociación",
            "url": None,
            "section": None,
            "version_label": None,
            "is_law": False,
            "jurisdiction": None,
            "scope_note": None,
            "valid_from": None,
        }
    ]
    assert d2["references"] == [
        {
            "category": "legal",
            "title": "Ley de datos",
            "source": "Diario Oficial",
            "url": "https://example.org/ley",
            "section": "Art. 5",
            "version_label": "2024-03",
            "is_law": True,
            "jurisdiction": "México",
            "scope_note": "Aplica solo en México",
            "valid_from": "2020-01-01",
        }
    ]
    # consecuencias con sus causas y relation_type
    got = [
        (c["kind"], c["relation_type"], c["node_key"], [x["node_key"] for x in c["causes"]])
        for c in body["consequences"]
    ]
    assert got == [("event", "causal", "EV", ["D"]), ("transition", "risk", "OUT_A", ["D"])], got
    # total = preguntas aplicables (CB no aplica a este recorrido), answered = respondidas
    res = {x["type"]: x for x in body["results"]}
    assert res["causal"] == {
        "type": "causal",
        "score": 100.0,
        "correct_count": 3,
        "answered": 3,
        "total": 3,
    }
    assert res["pretest"]["total"] == 2 and res["pretest"]["answered"] == 2


def test_rf011_results_total_son_las_aplicables_y_answered_las_respondidas(person, lenient_rich):
    sid = at_pretest_done(person, lenient_rich, {"P1": "b"})  # el conjunto no exige todas
    play_to_end(person, sid)
    res = {x["type"]: x for x in person.get(f"/api/v1/sessions/{sid}/summary").json()["results"]}
    assert res["pretest"] == {
        "type": "pretest",
        "score": 100.0,
        "correct_count": 1,
        "answered": 1,
        "total": 2,
    }
    assert res["causal"]["total"] == 3 and res["causal"]["answered"] == 3


def test_rf061_abandonar_no_impide_reanudar(person, superuser, rich):
    sid = start(person, rich)
    superuser.execute(
        "UPDATE nukyro.sessions SET started_at = now() - interval '40 days', "
        "last_activity_at = now() - interval '40 days' WHERE id = %s",
        (sid,),
    )
    fill(person, sid, "pretest", {"P1": "b", "P2": "a"})
    assert submit(person, sid, "pretest").status_code == 200
    started, outcome = row(
        superuser, "SELECT started_at, outcome_reached_at FROM nukyro.sessions WHERE id = %s", sid
    )
    cutoff = datetime.now(UTC) - timedelta(days=30)
    assert outcome is None and is_abandoned(started, outcome, cutoff) is True
    finish(person, sid, "A", ("R1",))  # avanza (200) y decide (200) pese al abandono
    reached = row(superuser, "SELECT outcome_reached_at FROM nukyro.sessions WHERE id = %s", sid)
    assert reached[0] is None  # D2 sigue pendiente: reanudar no cierra ni salta nada
    body = {"node_key": "D2", "option_key": "A2", "reason_keys": []}
    assert (
        person.post(f"/api/v1/sessions/{sid}/decisions", json=body, headers=WRITE).status_code
        == 200
    )


def test_rf057_defecto_11_el_resumen_es_409_hasta_terminar_las_evaluaciones(person, rich):
    sid = at_pretest_done(person, rich)
    assert person.get(f"/api/v1/sessions/{sid}/summary").status_code == 409
    finish(person, sid, "A", ("R1",))
    assert (
        person.get(f"/api/v1/sessions/{sid}/summary").status_code == 409
    )  # sin desenlace ni finales
