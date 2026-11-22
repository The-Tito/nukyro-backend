"""Caja negra del resumen (T-15): tres recorridos por HTTPS con lo esperado calculado a mano.

Solo se usa la API. El resumen no sale antes de terminar las evaluaciones (defecto 11) y nunca trae
alternativas no elegidas, correctas, valores de variables ni una nota global (RF-049).
"""

import pytest
from evaluaciones import EVALUACIONES, ORDEN_FINAL
from recorridos import RECORRIDOS
from test_assessment import (
    ACCEPT,
    WRITE,
    answer_all,
    do_pretest,
    keys,
    new_client,
    play,
    start,
    submit,
)

# Aciertos y total por evaluación, contados a mano sobre las respuestas de tests/evaluaciones.py
RESULTADOS = {
    "OUT_SOLID": {"pretest": (33.33, 2, 6), "posttest": (100.0, 6, 6), "transfer": (80.0, 4, 5),
                  "causal": (100.0, 1, 1)},
    "OUT_MIXED": {"pretest": (66.67, 4, 6), "posttest": (66.67, 4, 6), "transfer": (60.0, 3, 5),
                  "causal": (50.0, 1, 2)},
    "OUT_CRISIS": {"pretest": (0.0, 0, 6), "posttest": (83.33, 5, 6), "transfer": (40.0, 2, 5),
                   "causal": (66.67, 2, 3)},
}  # fmt: skip
# Justificaciones de las cuatro decisiones de H05 (D1, D5, D7, D8): aciertos a mano desde recorridos
H05 = {"OUT_SOLID": 4, "OUT_MIXED": 4, "OUT_CRISIS": 1}
# Diferencia post - pre en puntos
DIFERENCIA = {"OUT_SOLID": 66.67, "OUT_MIXED": 0.0, "OUT_CRISIS": 83.33}
# (relación, título, decisiones causantes) de cada consecuencia guardada
D1_6 = ["D1", "D2", "D3", "D4", "D5", "D6"]
CONSECUENCIAS = {
    "OUT_SOLID": [("causal", "Desenlace: plataforma sólida", D1_6)],
    "OUT_MIXED": [("risk", "Aviso: protección de datos baja", ["D1", "D2", "D6", "D7"])],
    "OUT_CRISIS": [
        ("causal", "Aviso: acceso bajo", ["D3", "D5"]),
        ("risk", "Aviso: protección de datos baja", ["D1", "D2"]),
        ("causal", "Desenlace: plataforma en crisis", D1_6),
    ],
}
PROHIBIDAS = {"is_correct", "correct", "variables", "value", "old_value", "new_value", "values"}
GLOBALES = {"total_score", "grade", "overall", "moral_score", "level", "judgment", "global_score"}


@pytest.fixture
def person():
    with new_client() as client:
        assert client.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
        yield client


def summary(client, sid):
    return client.get(f"/api/v1/sessions/{sid}/summary")


def finish(client, sid, outcome):
    do_pretest(client, sid, outcome)
    play(client, sid, outcome)
    for kind in ORDEN_FINAL:
        answer_all(client, sid, outcome, kind)
        assert submit(client, sid, kind).status_code == 200


def test_rf057_defecto_11_el_resumen_es_409_hasta_terminar_las_evaluaciones(person):
    sid = start(person)
    assert summary(person, sid).status_code == 409
    do_pretest(person, sid, "OUT_SOLID")
    assert summary(person, sid).status_code == 409
    play(person, sid, "OUT_SOLID")
    assert summary(person, sid).status_code == 409  # con desenlace, pero sin terminar
    for kind in ORDEN_FINAL[:-1]:
        answer_all(person, sid, "OUT_SOLID", kind)
        submit(person, sid, kind)
        assert summary(person, sid).status_code == 409  # falta la causal
    answer_all(person, sid, "OUT_SOLID", "causal")
    submit(person, sid, "causal")
    assert summary(person, sid).status_code == 200


def test_rf067_un_resumen_ajeno_o_inexistente_es_404_y_sin_cookie_401(person):
    sid = start(person)
    finish(person, sid, "OUT_SOLID")
    with new_client() as other:
        other.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
        assert summary(other, sid).status_code == 404
        assert summary(other, "no-es-un-uuid").status_code == 404
    with new_client() as anonymous:
        assert summary(anonymous, sid).status_code == 401


@pytest.mark.parametrize("outcome", RECORRIDOS)
def test_rf039_a_rf057_el_resumen_de_cada_recorrido_es_el_calculado_a_mano(person, outcome):
    sid = start(person)
    finish(person, sid, outcome)
    r = summary(person, sid)
    assert r.status_code == 200, r.text
    data = r.json()
    steps = RECORRIDOS[outcome]["steps"]
    # RF-039: historial en orden, con la alternativa y las razones elegidas
    assert [d["node_key"] for d in data["decisions"]] == [s[0] for s in steps]
    assert [d["option_key"] for d in data["decisions"]] == [s[1] for s in steps]
    assert [{x["key"] for x in d["reasons"]} for d in data["decisions"]] == [
        set(s[2]) for s in steps
    ]
    # Ninguna alternativa no elegida aparece: sus claves de los otros recorridos no salen
    chosen = {s[1] for s in steps}
    otras = {s[1] for o in RECORRIDOS for s in RECORRIDOS[o]["steps"]} - chosen
    assert not [k for k in otras if k in r.text]
    assert not keys(data) & (PROHIBIDAS | GLOBALES)
    # RF-040, RF-041: consecuencias con causantes y relación causal o de riesgo
    got = [(c["relation_type"], c["title"], [x["node_key"] for x in c["causes"]])
           for c in data["consequences"]]  # fmt: skip
    assert sorted(got) == sorted(CONSECUENCIAS[outcome])
    assert all(c["explanation"].strip() for c in data["consequences"])
    # RF-042, RF-043: retroalimentación general de la decisión; solo la de su alternativa
    assert all(d["feedback"] and {f["scope"] for f in d["feedback"]} <= {"decision", "option"}
               for d in data["decisions"])  # fmt: skip
    # RF-044 a RF-048: referencias por decisión; solo lo legal es ley, con su jurisdicción
    refs = [x for d in data["decisions"] for x in d["references"]]
    assert refs and all(x["title"] and x["source"] for x in refs)
    for x in refs:
        assert x["is_law"] == (x["category"] == "legal")
        assert (x["jurisdiction"] is not None) == x["is_law"]
        assert (x["scope_note"] is not None) == x["is_law"]
    d4 = next(d for d in data["decisions"] if d["node_key"] == "D4")
    assert [x["category"] for x in d4["references"]] == ["legal"]
    d2 = next(d for d in data["decisions"] if d["node_key"] == "D2")
    assert [x["category"] for x in d2["references"]] == ["professional"]  # no hereda las de D4
    # RF-049, RF-056: puntuaciones por evaluación, pre, post y diferencia
    by_type = {x["type"]: (x["score"], x["correct_count"], x["total"]) for x in data["results"]}
    assert by_type == RESULTADOS[outcome]
    assert [by_type[k][0] for k in ("pretest", "posttest")] == [
        EVALUACIONES[outcome][k][1] for k in ("pretest", "posttest")
    ]
    assert data["pretest_score"] == RESULTADOS[outcome]["pretest"][0]
    assert data["posttest_score"] == RESULTADOS[outcome]["posttest"][0]
    assert data["difference"] == pytest.approx(DIFERENCIA[outcome], abs=0.005)
    # RF-059: justificaciones de H05 con la rúbrica fijada
    assert data["justifications"] == {
        "correct_count": H05[outcome],
        "total": 4,
        "rubric_version": "1",
    }
    # Sin nota global de la persona
    assert not set(data) & GLOBALES
