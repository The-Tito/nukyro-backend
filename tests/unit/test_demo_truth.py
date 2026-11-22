# ruff: noqa: E501
"""DEMO-BECAS (T-13): lo que el escenario afirma es cierto en TODAS las rutas que lo muestran.

Se enumeran las 3^8 = 6 561 combinaciones de alternativas. Un evaluador independiente (efectos con
recorte y reglas escritas a mano, sin el motor) calcula valores, eventos y desenlace de cada ruta; el
motor puro confirma que coinciden. Luego, para cada clave causal marcada correcta se escribe un
predicado que debe cumplirse en toda ruta donde la pregunta se presenta, y cada distractor debe ser
falso en todas esas rutas. Los textos de eventos, desenlaces y explicaciones solo afirman lo que se
cumple en toda ruta que los muestra; donde no se puede garantizar, el texto es neutro.
"""

import itertools
import re
from dataclasses import dataclass
from functools import cache

from demo_spec import DECISIONS, NODES, SETS, SPEC, rows

from nukyro.engine.engine import advance, decide, initial_state
from nukyro.modules.simulation.service import _content

ORDER = [n["key"] for n in DECISIONS]  # D1 a D8
OPTIONS = {n["key"]: n["options"] for n in DECISIONS}
VARS = {v["key"]: v for v in SPEC["variables"]}
RULES = {r["key"]: r for r in SPEC["rules"]}
CONTENT = _content(rows())


@dataclass
class Route:
    choice: tuple  # claves de alternativa, de D1 a D8
    before: dict  # nodo -> valores antes de decidir
    after: dict  # nodo -> valores tras decidir
    events: list  # nodos evento mostrados
    outcome: str
    engine: tuple  # (desenlace, eventos) de dos ejecuciones del motor


def _apply(values, effects):
    values = dict(values)
    for e in effects:
        raw = values[e["variable_key"]] + e["value"] if e["op"] == "add" else e["value"]
        v = VARS[e["variable_key"]]
        values[e["variable_key"]] = max(v["min"], min(v["max"], raw))
    return values


def _independent(choice):
    """Evaluador independiente: reglas de demo/recorridos-esperados.md escritas a mano."""
    values = {k: v["initial"] for k, v in VARS.items()}
    before, after, events = {}, {}, []
    for node, option in zip(ORDER, choice, strict=True):
        effects = next(o["effects"] for o in OPTIONS[node] if o["key"] == option)
        before[node] = values
        values = _apply(values, effects)
        after[node] = values
        if node == "D6" and values["access"] <= 4:
            events.append("EV_ACCESS")
        if node == "D7" and values["privacy"] <= 4:
            events.append("EV_LEAK")
    p, a, q = (values[k] for k in ("privacy", "access", "quality"))
    if p <= 3 or (a <= 3 and q <= 4):
        outcome = "OUT_CRISIS"
    elif p >= 7 and a >= 6 and q >= 6:
        outcome = "OUT_SOLID"
    else:
        outcome = "OUT_MIXED"
    return before, after, events, outcome


def _engine(choice):
    state = advance(CONTENT, initial_state(CONTENT), "intro").state
    events = []
    for node, option in zip(ORDER, choice, strict=True):
        n = CONTENT.nodes[node]
        reasons = [next(r.key for r in n.reasons if r.correct)] if n.requires_justification else []
        result = decide(CONTENT, state, node, option, reasons)
        state = result.state
        events += [a.target_key for a in result.activations if a.kind == "event"]
    return state.current_node_key, events


@cache
def routes() -> tuple:
    out = []
    for choice in itertools.product(*[[o["key"] for o in OPTIONS[n]] for n in ORDER]):
        before, after, events, outcome = _independent(choice)
        out.append(
            Route(choice, before, after, events, outcome, (_engine(choice), _engine(choice)))
        )
    return tuple(out)


def shown(route: Route, target: str) -> bool:
    return target in route.events or route.outcome == target


def test_son_6561_rutas_y_el_evaluador_independiente_coincide_con_el_motor():
    assert len(routes()) == 6561
    for r in routes():
        assert r.engine[0] == r.engine[1]  # determinista hasta el desenlace
        assert r.engine[0] == (r.outcome, r.events), r.choice
    assert {r.outcome for r in routes()} == {"OUT_SOLID", "OUT_MIXED", "OUT_CRISIS"}
    assert {tuple(r.events) for r in routes()} == {
        (),
        ("EV_ACCESS",),
        ("EV_LEAK",),
        ("EV_ACCESS", "EV_LEAK"),
    }


# --- Predicados ---------------------------------------------------------------------------------


def changed(r, var, nodes):
    return any(r.before[n][var] != r.after[n][var] for n in nodes)


def final(r, var):
    return r.after["D8"][var]


def crisis(r):
    return final(r, "privacy") <= 3 or (final(r, "access") <= 3 and final(r, "quality") <= 4)


def solid(r):
    return final(r, "privacy") >= 7 and final(r, "access") >= 6 and final(r, "quality") >= 6


def sorteo(r):
    """«Fue al azar»: dos ejecuciones del mismo recorrido darían resultados distintos."""
    return r.engine[0] != r.engine[1]


@cache
def _groups(node, what):
    out = {}
    for r in routes():
        key = r.choice[ORDER.index(node)]
        out.setdefault(key, set()).add(what(r))
    return out


def solo_esa_decision(node, what):
    """«Solo esa decisión lo determinó»: con la misma alternativa en `node`, el resultado no
    cambia aunque cambien las demás decisiones."""
    return lambda r: len(_groups(node, what)[r.choice[ORDER.index(node)]]) == 1


def solo_la_variable(var, what):
    """«Solo esa medida lo determinó»: con el mismo valor final de la variable, el resultado no cambia."""
    groups = {}
    for r in routes():
        groups.setdefault(final(r, var), set()).add(what(r))
    return lambda r: len(groups[final(r, var)]) == 1


def outcome_of(r):
    return r.outcome


def event_of(name):
    return lambda r: name in r.events


# Por pregunta causal (clave `requires`): texto de la opción -> la afirmación es cierta en esa ruta.
CAUSAL = {
    "EV_ACCESS": {
        "El acceso quedó bajo al salir de las pruebas y eso activó el aviso.": lambda r: changed(r, "access", ORDER[:5]) and r.after["D6"]["access"] <= 4,
        "Apareció al azar, sin depender de ninguna medida del escenario.": sorteo,
        "Lo activó solo la decisión de pruebas, sin relación con las anteriores.": solo_esa_decision("D6", event_of("EV_ACCESS")),
    },
    "EV_LEAK": {
        "La protección de datos quedó baja tras la entrega y activó el aviso.": lambda r: changed(r, "privacy", ORDER[:6]) and r.after["D7"]["privacy"] <= 4,
        "Apareció al azar al cerrar la entrega, sin depender de ninguna medida.": sorteo,
        "Lo activó solo la decisión de entrega, sin relación con las decisiones anteriores.": solo_esa_decision("D7", event_of("EV_LEAK")),
    },
    "OUT_SOLID": {
        "Al terminar, datos, acceso y calidad quedaron en nivel alto a la vez.": solid,
        "Se asignó al azar al final, sin depender de las medidas del escenario.": sorteo,
        "Dependió solo de la última decisión, sin importar las anteriores.": solo_esa_decision("D8", outcome_of),
    },
    "OUT_MIXED": {
        "Al terminar, algún indicador quedó bajo el nivel alto, sin llegar al crítico.": lambda r: not solid(r) and not crisis(r),
        "Dependió solo de la protección de datos, sin importar las demás medidas.": solo_la_variable("privacy", outcome_of),
        "Se asignó al azar al final, sin depender de las medidas del escenario.": sorteo,
    },
    "OUT_CRISIS": {
        "Al terminar, la protección de datos quedó muy baja, o el acceso y la calidad bajos.": crisis,
        "Se asignó al azar al final, sin depender de ninguna de las medidas del escenario.": sorteo,
        "Dependió solo de la última decisión tomada, sin importar las anteriores.": solo_esa_decision("D8", outcome_of),
    },
}  # fmt: skip


def test_cada_causal_tiene_una_afirmacion_por_opcion_y_ninguna_de_mas():
    assert {q["requires"] for q in SETS["causal"]} == set(CAUSAL)
    for q in SETS["causal"]:
        labels = {o["label"] for o in q["options"]}
        assert labels == set(CAUSAL[q["requires"]]), q["key"]


def test_la_clave_correcta_es_cierta_y_cada_distractor_falso_en_toda_ruta_donde_se_presenta():
    for q in SETS["causal"]:
        claims = CAUSAL[q["requires"]]
        presented = [r for r in routes() if shown(r, q["requires"])]
        assert presented, q["key"]  # no es vacuamente cierto
        for o in q["options"]:
            values = {bool(claims[o["label"]](r)) for r in presented}
            assert values == {o["correct"]}, (q["key"], o["label"], values)


def test_toda_ruta_posible_recibe_al_menos_una_pregunta_causal():
    assert all(any(shown(r, q["requires"]) for q in SETS["causal"]) for r in routes())
    for q in SETS["causal"]:  # y solo se presentan las ligadas a algo que ocurrió (RF-058)
        assert (
            any(not shown(r, q["requires"]) for r in routes())
            or NODES[q["requires"]]["type"] == "outcome"
        )


# --- Textos de eventos, desenlaces y explicaciones ------------------------------------------------

TEXT = {  # nodo o regla -> [(frase del texto, afirmación que debe cumplirse en toda ruta que lo muestra)]
    "EV_ACCESS": [("nivel bajo", lambda r: r.after["D6"]["access"] <= 4)],
    "EV_LEAK": [("nivel bajo", lambda r: r.after["D7"]["privacy"] <= 4)],
    "OUT_SOLID": [("nivel alto a la vez", solid)],
    "OUT_MIXED": [
        ("por debajo del nivel alto", lambda r: not solid(r)),
        ("sin llegar a un nivel crítico", lambda r: not crisis(r)),
    ],
    "OUT_CRISIS": [("muy bajo, o el acceso y la calidad quedaron bajos a la vez", crisis)],
    "ev_access": [("en un nivel bajo", lambda r: r.after["D6"]["access"] <= 4)],
    "ev_leak": [("en un nivel bajo", lambda r: r.after["D7"]["privacy"] <= 4)],
    "tr_crisis": [("alguna de estas condiciones", crisis)],
    "tr_solid": [("a la vez", solid)],
}  # fmt: skip

FIRED = {
    "ev_access": lambda r: "EV_ACCESS" in r.events,
    "ev_leak": lambda r: "EV_LEAK" in r.events,
    "tr_crisis": lambda r: r.outcome == "OUT_CRISIS",
    "tr_solid": lambda r: r.outcome == "OUT_SOLID",
}
# Sin atribuir una decisión concreta ni un hecho narrado que pudo no ocurrir
FORBIDDEN = re.compile(
    r"redujer|redujo|aumentaron|bajaron|expuest|filtr|llegan incompletas|se ve que|un reporte muestra|tras la entrega|criterios publicados|explicar cada decisi",
    re.IGNORECASE,
)


def texts():
    for key, n in NODES.items():
        if n["type"] in ("event", "outcome"):
            yield key, n["body"], (lambda r, k=key: shown(r, k))
    for key, rule in RULES.items():
        yield key, rule["explanation"], FIRED[key]


def test_hay_afirmaciones_para_todo_evento_desenlace_y_explicacion():
    assert {k for k, _, _ in texts()} == set(TEXT)


def test_cada_texto_solo_afirma_lo_cierto_en_toda_ruta_que_lo_muestra():
    for key, body, is_shown in texts():
        assert not FORBIDDEN.search(body), (key, body)
        presented = [r for r in routes() if is_shown(r)]
        assert presented, key
        for phrase, claim in TEXT[key]:
            assert phrase in body, (key, phrase)
            assert all(claim(r) for r in presented), (key, phrase)
    for key in ("EV_ACCESS", "EV_LEAK"):  # los títulos tampoco narran lo que pudo no ocurrir
        assert not FORBIDDEN.search(NODES[key]["title"])


def test_la_longitud_y_la_posicion_de_la_correcta_no_la_revelan():
    """Ni la longitud ni la posición delatan la correcta: H02, H03 y H04 dependen de ello."""
    for name, questions in SETS.items():
        cap = -(-len(questions) // 3)  # ceil(n/3)
        by_rank = [0, 0, 0]  # corta, media, larga
        by_slot = {}
        for q in questions:
            sizes = [len(o["label"]) for o in q["options"]]
            assert len(set(sizes)) == len(sizes), (q["key"], "empate de longitud", sizes)
            assert max(sizes) <= 1.5 * min(sizes), (q["key"], sizes)
            at = next(i for i, o in enumerate(q["options"]) if o["correct"])
            by_rank[sorted(sizes).index(sizes[at])] += 1
            by_slot[at] = by_slot.get(at, 0) + 1
        assert max(by_rank) <= cap, (name, "rango de longitud (corta, media, larga)", by_rank, cap)
        assert max(by_slot.values()) <= cap, (name, "posición de la correcta", by_slot, cap)
