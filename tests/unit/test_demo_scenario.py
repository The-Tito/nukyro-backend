# ruff: noqa: E501
"""DEMO-BECAS (T-13, D-17): estructura, conteos, RF-066 y los tres recorridos con el motor puro."""

import re

import pytest
from demo_spec import DECISIONS, NODES, SETS, SPEC, rows, strings
from recorridos import RECORRIDOS, VARIABLES

from nukyro.engine.engine import advance, decide, initial_state
from nukyro.engine.validation import validate
from nukyro.modules.simulation.service import _content

PHASES = {"requirements", "design", "development", "testing", "delivery", "incident_response"}


def test_conteos_exactos():
    kinds = [n["type"] for n in SPEC["nodes"]]
    assert (kinds.count("decision"), kinds.count("event"), kinds.count("outcome")) == (8, 2, 3)
    assert kinds.count("intro") == 1 and len(SPEC["variables"]) == 3
    assert all(v["min"] is not None and v["max"] is not None for v in SPEC["variables"])
    assert [r["type"] for r in SPEC["rules"]].count("event") == 2
    assert [r["type"] for r in SPEC["rules"]].count("transition") >= 1
    assert {n["phase"] for n in DECISIONS} == PHASES
    # EVAL-DISENO: 6 pre y 6 post equivalentes, 5 casos de transferencia (H03), 5 causales
    assert {t: len(q) for t, q in SETS.items()} == {
        "pretest": 6, "posttest": 6, "transfer": 5, "causal": 5,
    }  # fmt: skip
    # RF-059 y H05: exactamente cuatro decisiones evaluadas, todas con justificación estructurada
    h05 = [n["key"] for n in DECISIONS if n.get("h05")]
    assert len(h05) == 4 and all(NODES[k]["requires_justification"] for k in h05)


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

    # RF-058: TODA pregunta causal se liga a un evento o desenlace
    for q in SETS["causal"]:
        assert q.get("requires") in NODES and NODES[q["requires"]]["type"] in ("event", "outcome")
    # y cada ruta posible recibe al menos una: hay preguntas para los tres desenlaces
    outcomes = {n["key"] for n in SPEC["nodes"] if n["type"] == "outcome"}
    assert outcomes <= {q["requires"] for q in SETS["causal"]}


SCENARIO_WORDS = (
    r"(beca|instituto|convocatoria|solicitud|solicitante|formulario|nukylandia|plataforma de)"
)


def test_pre_y_post_con_situaciones_distintas_y_transferencia_fuera_del_escenario():
    pre, post = SETS["pretest"], SETS["posttest"]
    for a, b in zip(pre, post, strict=True):
        assert a["prompt"] != b["prompt"]
        # situación distinta: ni el enunciado ni ninguna opción se repiten entre pre y post
        assert not {o["label"] for o in a["options"]} & {o["label"] for o in b["options"]}
    # H03: cinco situaciones nuevas, distintas entre sí y del escenario, sobre sus conceptos
    transfer = SETS["transfer"]
    assert len({q["prompt"] for q in transfer}) == 5
    for q in transfer:
        assert not re.search(SCENARIO_WORDS, q["prompt"].lower()), q["key"]
    objectives = {o["key"] for o in SPEC["objectives"]}
    assert {q["objective"] for q in transfer} == objectives


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


# --- Las razones y las alternativas no revelan la respuesta por orden ni por clave (T-13) ---

NEUTRAL = re.compile(
    r"^[a-z]+\d_[0-9a-f]{4}$"
)  # p. ej. «o3_9c1e»: sin letra de orden ni de acierto
BEST = {step[0]: step[1] for step in RECORRIDOS["OUT_SOLID"]["steps"]}  # la alternativa más sólida


def test_claves_neutras_de_alternativas_y_razones():
    for n in DECISIONS:
        keys = [o["key"] for o in n["options"]] + [r["key"] for r in n.get("reasons", [])]
        assert len(set(keys)) == len(keys)
        assert all(NEUTRAL.match(k) for k in keys), (n["key"], keys)


def test_posicion_de_la_correcta_variada_en_alternativas_y_razones():
    best = [[o["key"] for o in n["options"]].index(BEST[n["key"]]) for n in DECISIONS]
    assert len(set(best)) >= 3 and max(best.count(i) for i in set(best)) <= 3, best
    by_key = []
    for n in DECISIONS:
        keys = sorted(o["key"] for o in n["options"])
        by_key.append(keys.index(BEST[n["key"]]))
    assert len(set(by_key)) >= 2  # ni por clave la sólida es siempre la primera ni la última
    justified = [n for n in DECISIONS if n["requires_justification"]]
    first = [[r["correct"] for r in n["reasons"]].index(True) for n in justified]
    assert len(set(first)) >= 3, first  # la primera correcta cae en posiciones distintas
    for n in justified:
        flags = [r["correct"] for r in n["reasons"]]
        assert flags != sorted(flags, reverse=True), n["key"]  # no «todas las correctas primero»
        ranks = [
            sorted(r["key"] for r in n["reasons"]).index(r["key"])
            for r in n["reasons"]
            if r["correct"]
        ]
        assert ranks != list(range(len(ranks))), n["key"]  # ni por clave van primero


@pytest.mark.parametrize("name", ["pretest", "posttest", "transfer", "causal"])
def test_posicion_y_clave_de_la_correcta_varian_en_cada_conjunto_de_preguntas(name):
    qs = SETS[name]
    position = [[o["correct"] for o in q["options"]].index(True) for q in qs]
    key = [next(o["key"] for o in q["options"] if o["correct"]) for q in qs]
    assert len(set(position)) >= 3 and len(set(key)) >= 3
    assert max(position.count(i) for i in set(position)) <= (len(qs) + 1) // 2
    assert max(key.count(k) for k in set(key)) <= (len(qs) + 1) // 2


def test_la_correcta_de_pre_y_post_no_ocupa_la_misma_posicion():
    pos = lambda q: [o["correct"] for o in q["options"]].index(True)  # noqa: E731
    assert all(pos(a) != pos(b) for a, b in zip(SETS["pretest"], SETS["posttest"], strict=True))
