"""Validador de RF-066 (ADR-009 «Publicar exige», D-28): puro, sin base de datos."""

import copy

import pytest

from nukyro.engine.validation import Issue, validate

INT32 = 2**31 - 1


def base() -> dict:
    """Contenido válido: intro -> D1 -> D2 -> BUENO/MALO, con un evento EV."""

    def node(key, kind, nxt=None, point=False, just=False, min_correct=1):
        return {
            "key": key,
            "node_type": kind,
            "has_point": point,
            "requires_justification": just,
            "min_correct": min_correct,
            "default_next": nxt,
        }

    return {
        "nodes": [
            node("intro", "intro", "D1"),
            node("D1", "decision", "D2", point=True, just=True),
            node("D2", "decision", "BUENO", point=True),
            node("EV", "event"),
            node("MALO", "outcome"),
            node("BUENO", "outcome"),
        ],
        "variables": [{"key": "p", "initial_value": 3, "min_value": 0, "max_value": 5}],
        "options": [
            {
                "key": "A",
                "node_key": "D1",
                "effects": [{"variable_key": "p", "op": "add", "value": -2}],
                "next_key": None,
            },
            {"key": "B", "node_key": "D1", "effects": [], "next_key": None},
            {"key": "C", "node_key": "D2", "effects": [], "next_key": None},
        ],
        "reasons": [
            {"key": "R1", "node_key": "D1", "is_correct": True},
            {"key": "R2", "node_key": "D1", "is_correct": False},
        ],
        "rules": [
            {
                "key": "RE",
                "node_key": "D2",
                "rule_type": "event",
                "condition": {"var": "p", "op": "lt", "value": 2},
                "target_key": "EV",
            },
            {
                "key": "RT",
                "node_key": "D2",
                "rule_type": "transition",
                "condition": {"any": [{"var": "p", "op": "lte", "value": 1}, {"chose": "C"}]},
                "target_key": "MALO",
            },
        ],
        "objectives": ["LO"],
        "question_sets": [{"set_type": "pretest", "questions": [{"key": "Q1", "correct": 1}]}],
    }


def codes(rows) -> set[str]:
    return {i.code for i in validate(rows)}


def test_valido_no_tiene_errores():
    assert validate(base()) == []


def mutate(fn):
    rows = base()
    fn(rows)
    return rows


def node_of(rows, key):
    return next(n for n in rows["nodes"] if n["key"] == key)


def _event_to_option(r):
    r["options"][0]["next_key"] = "EV"


def _event_default(r):
    node_of(r, "intro")["default_next"] = "EV"


def _transition_to_event(r):
    r["rules"][1]["target_key"] = "EV"


def _event_rule_to_outcome(r):
    r["rules"][0]["target_key"] = "MALO"


def _unknown_option_target(r):
    r["options"][0]["next_key"] = "NADA"


def _unknown_default(r):
    node_of(r, "D2")["default_next"] = "NADA"


def _unknown_rule_target(r):
    r["rules"][1]["target_key"] = "NADA"


def _orphan(r):
    r["nodes"].append(
        {
            "key": "HUERFANO",
            "node_type": "outcome",
            "has_point": False,
            "requires_justification": False,
            "min_correct": 1,
            "default_next": None,
        }
    )


def _cycle(r):
    r["options"][2]["next_key"] = "D1"


def _no_exit_default(r):
    node_of(r, "D2")["default_next"] = None


def _no_exit_intro(r):
    node_of(r, "intro")["default_next"] = None


def _option_without_fallback(r):
    node_of(r, "D1")["default_next"] = None


def _no_point(r):
    node_of(r, "D2")["has_point"] = False


def _no_options(r):
    r["options"] = [o for o in r["options"] if o["node_key"] != "D2"] + []
    r["rules"][1]["condition"] = {"var": "p", "op": "lt", "value": 1}


def _two_intros(r):
    node_of(r, "EV")["node_type"] = "intro"


def _zero_intros(r):
    node_of(r, "intro")["node_type"] = "info"


def _outcome_exit(r):
    node_of(r, "MALO")["default_next"] = "BUENO"


def _outcome_rule(r):
    r["rules"].append(
        {
            "key": "RX",
            "node_key": "MALO",
            "rule_type": "transition",
            "condition": {"chose": "A"},
            "target_key": "BUENO",
        }
    )


def _outcome_option(r):
    r["options"].append({"key": "Z", "node_key": "MALO", "effects": [], "next_key": None})


CASES = [
    ("unknown_target", _unknown_option_target),
    ("unknown_target", _unknown_default),
    ("unknown_target", _unknown_rule_target),
    ("route_without_outcome", _event_to_option),
    ("route_without_outcome", _event_default),
    ("route_without_outcome", _transition_to_event),
    ("wrong_target_type", _event_rule_to_outcome),
    ("unreachable_node", _orphan),
    ("cycle", _cycle),
    ("route_without_outcome", _no_exit_default),
    ("route_without_outcome", _no_exit_intro),
    ("route_without_outcome", _option_without_fallback),
    ("decision_without_point", _no_point),
    ("decision_without_option", _no_options),
    ("intro_count", _two_intros),
    ("intro_count", _zero_intros),
    ("outcome_with_exits", _outcome_exit),
    ("outcome_with_exits", _outcome_rule),
    ("outcome_with_exits", _outcome_option),
]


@pytest.mark.parametrize("code,fn", CASES)
def test_cada_tipo_de_error_de_estructura_se_rechaza(code, fn):
    assert code in codes(mutate(fn))


def test_evento_cuenta_como_alcanzable_y_solo_alcanzado_por_regla_event():
    rows = base()
    assert "unreachable_node" not in codes(rows)
    rows["rules"] = [r for r in rows["rules"] if r["rule_type"] != "event"]
    assert Issue("unreachable_node", "EV") in validate(rows)


def test_una_transicion_que_puede_no_cumplirse_exige_salida_alternativa():
    rows = base()
    node_of(rows, "D2")["default_next"] = None
    rows["options"][2]["next_key"] = None
    assert Issue("route_without_outcome", "D2") in validate(rows)
    rows["options"][2]["next_key"] = "BUENO"  # la alternativa cubre la salida
    assert "route_without_outcome" not in codes(rows)


def test_error_de_ciclo_indica_un_nodo_del_ciclo():
    issues = validate(mutate(_cycle))
    assert any(i.code == "cycle" and i.key in {"D1", "D2"} for i in issues)


# --- Condiciones -----------------------------------------------------------


def cond(c):
    rows = base()
    rows["rules"][0]["condition"] = c
    return rows


def deep(n):
    c = {"chose": "A"}
    for _ in range(n):
        c = {"not": c}
    return c


BAD_CONDITIONS = [
    {"zzz": 1},
    {},
    {"var": "p", "op": "xx", "value": 1},
    {"var": "p", "op": "eq"},
    {"var": "p", "op": "eq", "value": "1"},
    {"var": "p", "op": "eq", "value": True},
    {"var": "p", "op": "eq", "value": 1.5},
    {"var": "p", "op": ["eq"], "value": 1},
    {"var": ["p"], "op": "eq", "value": 1},
    {"var": "p", "op": {"a": 1}, "value": 1},
    {"all": []},
    {"any": []},
    {"all": "x"},
    {"not": 3},
    {"chose": 3},
    {"visited": None},
    {"chose": "A", "visited": "D1"},
    deep(8),  # 9 niveles
    [1],
    "x",
    3,
    None,
]


@pytest.mark.parametrize("c", BAD_CONDITIONS, ids=lambda c: repr(c)[:40])
def test_condiciones_invalidas_dan_invalid_condition_sin_excepcion(c):
    assert Issue("invalid_condition", "RE") in validate(cond(c))


def test_profundidad_8_es_valida_y_9_no():
    assert "invalid_condition" not in codes(cond(deep(7)))  # 8 niveles
    assert "invalid_condition" in codes(cond(deep(8)))


def test_condicion_con_variable_inexistente():
    assert Issue("unknown_variable", "RE") in validate(cond({"var": "zz", "op": "eq", "value": 1}))


def test_condicion_con_alternativa_inexistente():
    assert Issue("unknown_option", "RE") in validate(cond({"all": [{"chose": "ZZ"}]}))


def test_condicion_con_nodo_inexistente():
    assert Issue("unknown_node", "RE") in validate(cond({"not": {"visited": "ZZ"}}))


def test_condiciones_validas_con_referencias_no_dan_error():
    ok = {
        "all": [{"visited": "D1"}, {"not": {"chose": "A"}}, {"var": "p", "op": "gte", "value": 0}]
    }
    assert validate(cond(ok)) == []


def test_json_arbitrario_no_lanza_excepciones():
    rows = base()
    rows["rules"][0]["condition"] = {"var": {"x": [1, {}]}, "op": [[]], "value": {}}
    rows["options"][0]["effects"] = [[], 3, None, {"variable_key": {}, "op": [], "value": []}]
    validate(rows)
    rows["options"][0]["effects"] = {"a": 1}
    validate(rows)
    rows["options"][0]["effects"] = None
    assert Issue("invalid_effect", "A") in validate(rows)


# --- Efectos y enteros -----------------------------------------------------


def eff(e):
    rows = base()
    rows["options"][0]["effects"] = e
    return rows


BAD_EFFECTS = [
    {"variable_key": "p", "op": "mul", "value": 1},
    {"variable_key": "p", "op": "add"},
    {"variable_key": "p", "op": "add", "value": "1"},
    {"variable_key": "p", "op": "add", "value": True},
    {"variable_key": "p", "op": "add", "value": 1, "extra": 1},
    {"variable_key": 3, "op": "add", "value": 1},
    {"variable_key": ["p"], "op": "add", "value": 1},
    {"variable_key": "p", "op": ["add"], "value": 1},
    "x",
    3,
]


@pytest.mark.parametrize("e", BAD_EFFECTS, ids=lambda e: repr(e)[:40])
def test_efectos_invalidos(e):
    assert Issue("invalid_effect", "A") in validate(eff([e]))


def test_efecto_con_variable_inexistente():
    r = eff([{"variable_key": "zz", "op": "add", "value": 1}])
    assert Issue("unknown_variable", "A") in validate(r)


def test_efectos_que_no_son_lista():
    assert Issue("invalid_effect", "A") in validate(eff({"variable_key": "p"}))


@pytest.mark.parametrize("v", [INT32 + 1, -INT32 - 2, 2**70])
def test_efecto_fuera_de_int32(v):
    assert Issue("int_out_of_range", "A") in validate(
        eff([{"variable_key": "p", "op": "set", "value": v}])
    )


def test_limites_de_int32_son_validos():
    r = eff(
        [
            {"variable_key": "p", "op": "set", "value": INT32},
            {"variable_key": "p", "op": "set", "value": -INT32 - 1},
        ]
    )
    assert "int_out_of_range" not in codes(r)


def test_variable_fuera_de_int32():
    r = base()
    r["variables"][0]["max_value"] = INT32 + 1
    assert Issue("int_out_of_range", "p") in validate(r)


def test_minimo_mayor_que_maximo():
    r = base()
    r["variables"][0].update(min_value=6, max_value=5)
    assert Issue("invalid_range", "p") in validate(r)


def unbounded(adds, initial=0):
    r = base()
    r["variables"] = [{"key": "p", "initial_value": initial, "min_value": None, "max_value": None}]
    r["options"][0]["effects"] = [{"variable_key": "p", "op": "add", "value": a} for a in adds]
    return r


def test_suma_acumulada_sin_limites_que_desborda_int32():
    # D1 aporta hasta 2^31-1 y D2 otro tanto: la suma desborda el integer de la base
    r = unbounded([INT32])
    r["options"][2]["effects"] = [{"variable_key": "p", "op": "add", "value": 5}]
    assert Issue("variable_overflow", "p") in validate(r)


def test_suma_acumulada_sin_limites_dentro_de_int32_es_valida():
    assert validate(unbounded([1000, 1000])) == []


def test_una_variable_con_un_solo_limite_tambien_puede_desbordar():
    r = unbounded([INT32, 1])
    r["variables"][0]["min_value"] = 0
    assert Issue("variable_overflow", "p") in validate(r)


def test_variable_con_ambos_limites_no_desborda():
    r = unbounded([INT32, INT32])
    r["variables"][0].update(min_value=0, max_value=10)
    assert "variable_overflow" not in codes(r)


def test_set_no_acumula_pero_su_magnitud_cuenta():
    r = unbounded([])
    r["options"][0]["effects"] = [{"variable_key": "p", "op": "set", "value": INT32}]
    r["options"][2]["effects"] = [{"variable_key": "p", "op": "add", "value": 1}]
    assert Issue("variable_overflow", "p") in validate(r)


# --- Justificación y evaluaciones -------------------------------------------


def test_justificacion_sin_correctas_suficientes():
    r = base()
    node_of(r, "D1")["min_correct"] = 2
    assert Issue("insufficient_correct_reasons", "D1") in validate(r)


def test_justificacion_sin_razones():
    r = base()
    r["reasons"] = []
    assert Issue("insufficient_correct_reasons", "D1") in validate(r)


def test_justificacion_con_minimo_cero():
    r = base()
    node_of(r, "D1")["min_correct"] = 0
    assert Issue("invalid_min_correct", "D1") in validate(r)


def test_sin_justificacion_no_exige_razones():
    r = base()
    node_of(r, "D1")["requires_justification"] = False
    r["reasons"] = []
    assert validate(r) == []


def test_pretest_ausente():
    r = base()
    r["question_sets"] = []
    assert Issue("pretest_missing", None) in validate(r)


def test_pretest_sin_preguntas():
    r = base()
    r["question_sets"] = [{"set_type": "pretest", "questions": []}]
    assert Issue("pretest_empty", None) in validate(r)


@pytest.mark.parametrize("n", [0, 2])
def test_pretest_con_pregunta_sin_exactamente_una_correcta(n):
    r = base()
    r["question_sets"][0]["questions"].append({"key": "Q2", "correct": n})
    assert Issue("question_correct_count", "Q2") in validate(r)


@pytest.mark.parametrize("kind", ["posttest", "transfer", "causal"])
def test_toda_pregunta_de_los_demas_conjuntos_tiene_una_correcta(kind):
    r = base()
    r["question_sets"].append({"set_type": kind, "questions": [{"key": "QX", "correct": 0}]})
    assert Issue("question_correct_count", "QX") in validate(r)


def test_sin_objetivos_rn10():
    r = base()
    r["objectives"] = []
    assert Issue("no_objectives", None) in validate(r)


def test_acumula_todos_los_errores_y_no_muta_la_entrada():
    r = base()
    r["objectives"] = []
    r["question_sets"] = []
    node_of(r, "D1")["min_correct"] = 0
    before = copy.deepcopy(r)
    assert {i.code for i in validate(r)} >= {
        "no_objectives",
        "pretest_missing",
        "invalid_min_correct",
    }
    assert r == before


@pytest.mark.parametrize("fn", [_event_to_option, _event_default, _transition_to_event])
def test_un_evento_en_la_ruta_es_valido_si_tiene_salida(fn):
    rows = mutate(fn)
    node_of(rows, "EV")["default_next"] = "MALO" if fn is not _event_default else "D1"
    assert validate(rows) == []


def test_un_ciclo_a_traves_de_un_evento_se_rechaza():
    rows = mutate(_event_to_option)
    node_of(rows, "EV")["default_next"] = "D1"
    assert "cycle" in codes(rows)


def test_la_salida_de_un_evento_solo_mostrado_no_hace_alcanzable_un_nodo():
    rows = base()
    node_of(rows, "EV")["default_next"] = "OCULTO"
    _orphan(rows)
    rows["nodes"][-1]["key"] = "OCULTO"
    assert Issue("unreachable_node", "OCULTO") in validate(rows)
