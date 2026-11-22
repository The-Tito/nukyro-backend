"""Pruebas del motor puro (ADR-009): sin base de datos ni HTTP."""

import copy

import pytest

from nukyro.engine.conditions import evaluate
from nukyro.engine.engine import advance, decide, initial_state
from nukyro.engine.model import (
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
    Variable,
)


def _vars():
    return {k: Variable(k, 3, 0, 5) for k in ("p", "e")}


def _outcomes(*keys):
    return {k: Node(k, "outcome") for k in keys}


# --- Contenido de los ejemplos de ADR-009 ---------------------------------

_ANY = {"any": [{"var": "p", "op": "lte", "value": 1}, {"chose": "D"}]}
EXAMPLE = Content(
    nodes={
        "intro": Node("intro", "intro", default_next_node_key="D1"),
        "D1": Node(
            "D1",
            "decision",
            options=(
                Option("A", (Effect("p", "add", -2),)),
                Option("B", (Effect("p", "add", 3),)),
            ),
            default_next_node_key="D2",
        ),
        "D2": Node(
            "D2",
            "decision",
            options=(
                Option("C", (Effect("e", "add", 1),)),
                Option("D", (Effect("p", "add", -2),)),
            ),
            default_next_node_key="BUENO",
        ),
        "EV": Node("EV", "event"),
        **_outcomes("MALO", "BUENO"),
    },
    variables=_vars(),
    rules=(
        Rule("ev", "D2", "event", 1, {"var": "p", "op": "lt", "value": 2}, "EV", "influye", "x"),
        Rule("malo", "D2", "transition", 10, _ANY, "MALO", "determina", "y"),
    ),
)


def _play(content, *picks):
    st = advance(content, initial_state(content), "intro").state
    results = []
    for node, opt in picks:
        r = decide(content, st, node, opt, ())
        st = r.state
        results.append(r)
    return st, results


@pytest.mark.parametrize(
    ("picks", "p", "e", "event", "final", "ev_causes", "tr_causes"),
    [
        ("AC", 1, 4, True, "MALO", ("D1",), ("D1",)),
        ("AD", 0, 3, True, "MALO", ("D1", "D2"), ("D1", "D2")),
        ("BC", 5, 4, False, "BUENO", None, None),
        ("BD", 3, 3, False, "MALO", None, ("D2",)),
    ],
)
def test_adr_examples(picks, p, e, event, final, ev_causes, tr_causes):
    st, rs = _play(EXAMPLE, ("D1", picks[0]), ("D2", picks[1]))
    assert (st.values["p"], st.values["e"]) == (p, e)
    assert st.current_node_key == final
    assert st.path == ("intro", "D1", "D2", final)
    acts = rs[1].activations
    events = [a for a in acts if a.kind == "event"]
    trans = [a for a in acts if a.kind == "transition"]
    assert bool(events) is event
    if event:
        assert events[0].target_key == "EV" and events[0].causes == ev_causes
        assert events[0].relation_type == "influye"
    assert (trans[0].causes if trans else None) == tr_causes
    assert rs[1].next_node_key == final


def test_clamp_keeps_previous_value():
    _, rs = _play(EXAMPLE, ("D1", "A"), ("D2", "D"))
    assert rs[1].effects == (AppliedEffect("p", 1, 0),)
    _, rs = _play(EXAMPLE, ("D1", "B"))
    assert rs[0].effects == (AppliedEffect("p", 3, 5),)


# --- Condiciones -----------------------------------------------------------


def ev(cond, values=None, decisions=(), path=()):
    return evaluate(cond, values or {"p": 3}, tuple(decisions), tuple(path))


@pytest.mark.parametrize(
    ("op", "value", "expected"),
    [
        ("eq", 3, True), ("eq", 2, False),
        ("ne", 2, True), ("ne", 3, False),
        ("lt", 4, True), ("lt", 3, False),
        ("lte", 3, True), ("lte", 2, False),
        ("gt", 2, True), ("gt", 3, False),
        ("gte", 3, True), ("gte", 4, False),
    ],
)  # fmt: skip
def test_var_operators(op, value, expected):
    assert ev({"var": "p", "op": op, "value": value})[0] is expected


def _d(node, option, *effects):
    return Decision(node, option, (), True, tuple(AppliedEffect(*x) for x in effects), (), None)


D1 = _d("D1", "A", ("p", 3, 1))
D2 = _d("D2", "X", ("p", 1, 1), ("e", 3, 4))
LOW = {"var": "p", "op": "lte", "value": 1}


def test_chose_visited_and_combinators():
    vals = {"p": 1, "e": 4}
    assert ev({"chose": "A"}, vals, [D1]) == (True, frozenset({"D1"}))
    assert ev({"chose": "Z"}, vals, [D1]) == (False, frozenset())
    assert ev({"visited": "D1"}, vals, [D1], ["D1"]) == (True, frozenset())
    assert ev({"visited": "D9"}, vals, [D1], ["D1"])[0] is False
    assert ev({"all": [LOW, {"chose": "A"}]}, vals, [D1])[0] is True
    assert ev({"all": [LOW, {"chose": "Z"}]}, vals, [D1])[0] is False
    assert ev({"any": [{"chose": "Z"}, LOW]}, vals, [D1])[0] is True
    assert ev({"any": [{"chose": "Z"}, {"chose": "Y"}]}, vals, [D1])[0] is False
    assert ev({"not": {"chose": "Z"}}, vals, [D1])[0] is True
    assert ev({"not": LOW}, vals, [D1])[0] is False


def test_causes():
    vals = {"p": 1, "e": 4}
    ds = [D1, D2]
    # un efecto sin cambio no es causa
    assert ev(LOW, vals, ds)[1] == frozenset({"D1"})
    # la rama falsa del any no se atribuye
    assert ev({"any": [LOW, {"chose": "Z"}]}, vals, ds)[1] == frozenset({"D1"})
    # all: unión de sus partes
    cond = {"all": [LOW, {"var": "e", "op": "gt", "value": 3}]}
    assert ev(cond, vals, ds)[1] == frozenset({"D1", "D2"})
    # not: quienes cambiaron las variables que menciona
    assert ev({"not": {"var": "e", "op": "gt", "value": 9}}, vals, ds)[1] == frozenset({"D2"})


@pytest.mark.parametrize(
    "bad",
    [
        {"var": "p", "op": "eq", "value": True},
        {"var": "p", "op": "xx", "value": 1},
        {"var": "p", "op": "eq"},
        {"foo": 1},
        {"all": []},
        {"any": []},
        {"chose": 1},
        {"not": {"foo": 1}},
        [1],
        {"chose": "A", "visited": "B"},
    ],
)
def test_invalid_grammar(bad):
    with pytest.raises(InvalidContent):
        ev(bad)


def test_depth_limit():
    cond = {"chose": "A"}
    for _ in range(7):
        cond = {"not": cond}  # profundidad 8
    ev(cond)
    with pytest.raises(InvalidContent):
        ev({"not": cond})  # profundidad 9


# --- Precedencia, eventos y avance ----------------------------------------


def mini(rules=(), a_next=None):
    return Content(
        nodes={
            "intro": Node("intro", "intro", default_next_node_key="X"),
            "X": Node(
                "X",
                "decision",
                options=(Option("a", (Effect("p", "add", 1),), a_next),),
                default_next_node_key="DEF",
            ),
            "E1": Node("E1", "event"),
            "E2": Node("E2", "event"),
            **_outcomes("DEF", "T1", "T2"),
        },
        variables={"p": Variable("p", 0, 0, 5)},
        rules=tuple(rules),
    )


TRUE = {"var": "p", "op": "gte", "value": 1}


def _r(key, kind, prio, target, cond=TRUE):
    return Rule(key, "X", kind, prio, cond, target, "influye", "t")


def _go(content):
    st = advance(content, initial_state(content), "intro").state
    return decide(content, st, "X", "a", ())


def test_precedence():
    assert _go(mini()).next_node_key == "DEF"
    assert _go(mini(a_next="T1")).next_node_key == "T1"
    # la transición gana a la alternativa
    assert _go(mini([_r("t", "transition", 1, "T2")], "T1")).next_node_key == "T2"
    # menor prioridad primero
    rules = [_r("a", "transition", 2, "T1"), _r("b", "transition", 1, "T2")]
    assert _go(mini(rules)).next_node_key == "T2"
    # misma prioridad: por clave
    rules = [_r("b", "transition", 1, "T2"), _r("a", "transition", 1, "T1")]
    assert _go(mini(rules)).next_node_key == "T1"
    # transición falsa no gana
    false = {"var": "p", "op": "gt", "value": 9}
    assert _go(mini([_r("t", "transition", 1, "T2", false)])).next_node_key == "DEF"


def test_events_do_not_change_route():
    rules = [_r("e2", "event", 2, "E2"), _r("e1", "event", 1, "E1")]
    r = _go(mini(rules))
    assert [a.target_key for a in r.activations] == ["E1", "E2"]
    assert r.next_node_key == "DEF"
    assert r.state.path == ("intro", "X", "DEF")


def test_advance():
    st = initial_state(EXAMPLE)
    r = advance(EXAMPLE, st, "intro")
    assert not r.replayed and r.next_node_key == "D1"
    assert r.state.current_node_key == "D1" and r.state.path == ("intro", "D1")
    again = advance(EXAMPLE, r.state, "intro")
    assert again.replayed and again.state == r.state
    with pytest.raises(DomainError) as e:
        advance(EXAMPLE, r.state, "D1")
    assert e.value.code == "decision_pending"
    with pytest.raises(DomainError) as e:
        advance(EXAMPLE, r.state, "D2")
    assert e.value.code == "node_not_current"
    with pytest.raises(DomainError) as e:
        advance(EXAMPLE, r.state, "nope")
    assert e.value.code == "unknown_node"
    end, _ = _play(EXAMPLE, ("D1", "B"), ("D2", "C"))
    with pytest.raises(DomainError) as e:
        advance(EXAMPLE, end, "BUENO")
    assert e.value.code == "not_advanceable"


def test_retry_returns_confirmed_even_after_advancing():
    st, rs = _play(EXAMPLE, ("D1", "A"), ("D2", "C"))
    again = decide(EXAMPLE, st, "D1", "B", ())
    assert again.replayed and again.state == st
    assert again.effects == rs[0].effects == (AppliedEffect("p", 3, 1),)
    assert again.next_node_key == "D2"
    assert st.decisions[0].option_key == "A"


# --- Justificación y rechazos ----------------------------------------------


def jx(min_correct=1):
    reasons = (Reason("r1", True), Reason("r2", True), Reason("r3", False))
    return Content(
        nodes={
            "intro": Node("intro", "intro", default_next_node_key="J"),
            "J": Node(
                "J",
                "decision",
                options=(Option("o"),),
                reasons=reasons,
                requires_justification=True,
                min_correct=min_correct,
                default_next_node_key="END",
            ),
            "END": Node("END", "outcome"),
        },
        variables={},
        rules=(),
    )


def _justify(content, reasons):
    st = advance(content, initial_state(content), "intro").state
    return decide(content, st, "J", "o", reasons).state.decisions[0].correct


@pytest.mark.parametrize(
    ("reasons", "ok"),
    [
        (("r1",), True),
        (("r1", "r2"), True),
        (("r1", "r3"), False),
        (("r1", "r2", "r3"), False),  # marcar todas no aprueba
        (("r3",), False),
    ],
)
def test_justification(reasons, ok):
    assert _justify(jx(), reasons) is ok


def test_justification_minimum():
    assert _justify(jx(2), ("r1",)) is False
    assert _justify(jx(2), ("r1", "r2")) is True


@pytest.mark.parametrize("min_correct", [1, 2])
def test_defecto_10_marcar_todas_las_razones_no_aprueba(min_correct):
    """Defecto 10 (RF-059, H05): con la regla vieja (solo el mínimo de correctas), marcarlas todas,
    incorrectas incluidas, aprobaba. Se aprueba con el mínimo correcto y ninguna incorrecta."""
    content = jx(min_correct)
    todas = tuple(r.key for r in content.nodes["J"].reasons)
    assert _justify(content, todas) is False
    assert _justify(content, ("r1", "r2")) is True


def _code(fn):
    with pytest.raises(DomainError) as e:
        fn()
    return e.value.code


def test_rejections():
    c = jx()
    st = advance(c, initial_state(c), "intro").state
    assert _code(lambda: decide(c, st, "J", "o", ())) == "reasons_required"
    assert _code(lambda: decide(c, st, "J", "o", ("r1", "r1"))) == "duplicate_reason"
    assert _code(lambda: decide(c, st, "J", "o", ("zz",))) == "unknown_reason"
    assert _code(lambda: decide(c, st, "J", "zz", ("r1",))) == "unknown_option"
    assert _code(lambda: decide(c, st, "nope", "o", ("r1",))) == "unknown_node"
    assert _code(lambda: decide(c, st, "END", "o", ())) == "node_not_current"
    assert _code(lambda: decide(c, initial_state(c), "intro", "o", ())) == "not_a_decision"
    m = mini()
    ms = advance(m, initial_state(m), "intro").state
    assert _code(lambda: decide(m, ms, "X", "a", ("r1",))) == "reasons_not_allowed"
    assert (
        _code(lambda: decide(EXAMPLE, initial_state(EXAMPLE), "D2", "C", ())) == "node_not_current"
    )


def test_invalid_effect_is_invalid_content():
    bad = mini()
    c = Content(
        nodes=bad.nodes,
        variables=bad.variables,
        rules=(),
    )
    c.nodes["X"] = Node(
        "X",
        "decision",
        options=(Option("a", (Effect("p", "mul", 1),)),),
        default_next_node_key="DEF",
    )
    assert _code(lambda: _go(c)) == "invalid_effect"


# --- Pureza ------------------------------------------------------------------


def test_input_not_mutated_and_deterministic():
    st = advance(EXAMPLE, initial_state(EXAMPLE), "intro").state
    before_state, before_content = copy.deepcopy(st), copy.deepcopy(EXAMPLE)
    r1 = decide(EXAMPLE, st, "D1", "A", ())
    r2 = decide(EXAMPLE, st, "D1", "A", ())
    assert st == before_state and EXAMPLE == before_content
    assert r1 == r2


def test_un_evento_en_la_ruta_si_avanza():
    content = Content(
        nodes={
            "intro": Node("intro", "intro", default_next_node_key="EV"),
            "EV": Node("EV", "event", default_next_node_key="FIN"),
            **_outcomes("FIN"),
        },
        variables=_vars(),
        rules=(),
    )
    at_event = advance(content, initial_state(content), "intro").state
    assert advance(content, at_event, "EV").finished


def test_variable_sin_limites_y_decision_sin_justificacion():
    content = Content(
        nodes={
            "intro": Node("intro", "intro", default_next_node_key="D1"),
            "D1": Node(
                "D1",
                "decision",
                options=(Option("A", (Effect("p", "add", -9),)),),
                default_next_node_key="FIN",
            ),
            **_outcomes("FIN"),
        },
        variables={"p": Variable("p", 3, None, None)},  # el esquema admite límites nulos
        rules=(),
    )
    at_decision = advance(content, initial_state(content), "intro").state
    state = decide(content, at_decision, "D1", "A", ()).state
    assert state.values["p"] == -6
    assert state.decisions[0].correct is None


# --- T-13: RF-028, RF-023 y determinismo hasta el desenlace ------------------------------------


def _orden_content():
    """p entre 0 y 10 desde 3. S: fija 8 y suma 5; T: suma 5 y fija 8."""
    return Content(
        nodes={
            "intro": Node("intro", "intro", default_next_node_key="D1"),
            "D1": Node(
                "D1",
                "decision",
                options=(
                    Option("S", (Effect("p", "set", 8), Effect("p", "add", 5))),
                    Option("T", (Effect("p", "add", 5), Effect("p", "set", 8))),
                ),
                default_next_node_key="FIN",
            ),
            **_outcomes("FIN"),
        },
        variables={"p": Variable("p", 3, 0, 10)},
        rules=(),
    )


def test_rf028_set_y_add_sobre_la_misma_variable_se_aplican_en_orden_con_recorte():
    content = _orden_content()
    start = advance(content, initial_state(content), "intro").state
    s = decide(content, start, "D1", "S", ())
    # fija 8 (3->8) y suma 5 sobre ese 8: 13 se recorta a 10. Invertir el orden daría (3,8),(8,8)
    assert s.effects == (AppliedEffect("p", 3, 8), AppliedEffect("p", 8, 10))
    assert s.state.values["p"] == 10
    t = decide(content, start, "D1", "T", ())
    assert t.effects == (AppliedEffect("p", 3, 8), AppliedEffect("p", 8, 8))
    assert t.state.values["p"] == 8


def _dos_justificadas():
    return Content(
        nodes={
            "intro": Node("intro", "intro", default_next_node_key="J1"),
            "J1": Node(
                "J1",
                "decision",
                options=(Option("o1", (Effect("p", "add", 1),)),),
                reasons=(Reason("ra", True), Reason("rb", False)),
                requires_justification=True,
                default_next_node_key="J2",
            ),
            "J2": Node(
                "J2",
                "decision",
                options=(Option("o2"),),
                reasons=(Reason("rc", True), Reason("rd", False)),
                requires_justification=True,
                default_next_node_key="END",
            ),
            "END": Node("END", "outcome"),
        },
        variables={"p": Variable("p", 3, 0, 10)},
        rules=(),
    )


def test_rf023_una_razon_existente_de_otro_nodo_justificado_se_rechaza_sin_cambios():
    c = _dos_justificadas()
    st = advance(c, initial_state(c), "intro").state
    before = copy.deepcopy(st)
    # «rc» existe y es correcta, pero es de J2: en J1 es una razón desconocida
    assert _code(lambda: decide(c, st, "J1", "o1", ("rc",))) == "unknown_reason"
    assert _code(lambda: decide(c, st, "J1", "o1", ("ra", "rc"))) == "unknown_reason"
    assert st == before and st.values["p"] == 3
    assert decide(c, st, "J1", "o1", ("ra",)).state.decisions[0].correct is True


def test_determinista_hasta_el_desenlace():
    """Mismo recorrido, mismo resultado completo en cada paso hasta el desenlace."""

    def run(first, second):
        st = advance(EXAMPLE, initial_state(EXAMPLE), "intro").state
        steps = []
        for node, option in (("D1", first), ("D2", second)):
            r = decide(EXAMPLE, st, node, option, ())
            st = r.state
            steps.append(r)
        return steps, st

    for picks in ("AC", "AD", "BC", "BD"):
        one, two = run(*picks), run(*picks)
        assert one == two
        assert one[1].current_node_key in ("MALO", "BUENO") and one[0][-1].finished
