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
import unicodedata
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
INICIAL = lambda var: VARS[var]["initial"]  # noqa: E731
CAUSAL = {
    "EV_ACCESS": {
        "Tras las pruebas el acceso quedó en un nivel bajo, y eso activó el aviso.": lambda r: changed(r, "access", ORDER[:5]) and r.after["D6"]["access"] <= 4,
        "El acceso subió a un nivel alto al salir de las pruebas y eso activó el aviso.": lambda r: r.after["D6"]["access"] >= 7,
        "El acceso ya estaba bajo antes de la primera decisión y eso activó el aviso.": lambda r: INICIAL("access") <= 4,
    },
    "EV_LEAK": {
        "Tras la entrega la protección de datos quedó en un nivel bajo, y eso activó el aviso.": lambda r: changed(r, "privacy", ORDER[:6]) and r.after["D7"]["privacy"] <= 4,
        "La protección de datos subió a un nivel alto tras la entrega y activó el aviso.": lambda r: r.after["D7"]["privacy"] >= 7,
        "La protección de datos empezó la partida en un nivel bajo y eso activó el aviso.": lambda r: INICIAL("privacy") <= 4,
    },
    "OUT_SOLID": {
        "Al terminar, datos, acceso y calidad quedaron en nivel alto a la vez.": solid,
        "Al terminar, la protección de datos quedó muy baja y eso decidió el desenlace.": lambda r: final(r, "privacy") <= 3,
        "Al terminar, el acceso quedó bajo y eso decidió el desenlace.": lambda r: final(r, "access") <= 5,
    },
    "OUT_MIXED": {
        "Al terminar, algún indicador estaba bajo el nivel alto, sin llegar al crítico.": lambda r: not solid(r) and not crisis(r),
        "Al terminar, datos, acceso y calidad quedaron en nivel alto a la vez.": solid,
        "Al terminar, el acceso y la calidad quedaron bajos a la vez, y eso decidió el desenlace.": lambda r: final(r, "access") <= 3 and final(r, "quality") <= 4,
    },
    "OUT_CRISIS": {
        "Al terminar, la protección de datos estaba muy baja, o bien el acceso y la calidad estaban bajos.": crisis,
        "Al terminar, datos, acceso y calidad quedaron en nivel alto a la vez.": solid,
        "Al terminar, ningún indicador llegó al nivel crítico, aunque alguno quedó bajo el alto.": lambda r: not crisis(r),
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


ORDENES = {  # las cinco maneras de ordenar sin leer el contenido: (indice, elemento) -> clave de orden
    "caracteres": lambda i, x: (len(x["label"]), i),
    "palabras": lambda i, x: (len(x["label"].split()), i),
    "alfabetico": lambda i, x: (re.sub("[^a-z ]", "", _plano(x["label"])), i),
    "clave": lambda i, x: (x["key"], i),
    "posicion": lambda i, x: (i, i),
}
MULETILLAS = (
    "azar",
    "sorteo",
    "solo",
    "solamente",
    "siempre",
    "nunca",
    "nadie",
    "unicamente",
    "cualquier",
)


def _plano(texto):
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c)
    )


def _ordenar(xs, f):
    return [x for _, x in sorted(enumerate(xs), key=lambda p: f(*p))]


def estrategias_ciegas(sets, decisiones):
    """Lista CERRADA de estrategias que no leen el contenido; ninguna debe aprobar H02 a H05.

    Preguntas: ordenar las opciones por caracteres, palabras, letras iniciales, clave o posicion y
    elegir un rango fijo (primero, segundo, tercero); o descartar las que contienen una muletilla y
    elegir la unica que queda. Razones: un rango fijo desde cada extremo o un corte contiguo fijo.
    Devuelve las estrategias que aprueban (lista vacia = ninguna)."""
    max_ok = {k: (3 if k == "transfer" else 2) for k in sets}  # H03: se aprueba con 4 de 5
    max_ok["pretest"] = max_ok["posttest"] = 3  # 3 de 6 = 50 %, por debajo del 80 % de H02
    malo = []
    for k, q in sets.items():
        for nombre, f in ORDENES.items():
            for r in range(3):
                n = sum(bool(_ordenar(x["options"], f)[r].get("correct")) for x in q)
                if n > max_ok[k]:
                    malo.append((k, nombre, f"rango {r}", f"{n}/{len(q)}"))
        n = 0
        for x in q:
            queda = [
                o
                for o in x["options"]
                if not set(re.findall("[a-z]+", _plano(o["label"]))) & set(MULETILLAS)
            ]
            n += len(queda) == 1 and bool(queda[0].get("correct"))
        if n > 1:
            malo.append((k, "muletillas", "", f"{n}/{len(q)}"))
    ds = [n for n in decisiones if n.get("h05")]
    cortes = [(f"rango {i}", lambda r, i=i: r[i : i + 1]) for i in range(4)]
    cortes += [
        (f"rango -{i + 1}", lambda r, i=i: r[len(r) - 1 - i : len(r) - i] if i < len(r) else [])
        for i in range(4)
    ]
    cortes += [
        (f"[{a}:{b}]", lambda r, a=a, b=b: r[a:b])
        for a, b in ((0, 2), (1, 3), (2, 4), (1, -1), (1, -2), (2, -1), (-2, None))
    ]
    for nombre, f in ORDENES.items():
        for c, g in cortes:
            n = 0
            for x in ds:
                s = g(_ordenar(x["reasons"], f))
                n += len(s) >= x.get("min_correct", 1) and all(o.get("correct") for o in s)
            if n > 2:
                malo.append(("H05", nombre, c, f"{n}/4"))
    return malo


def test_ninguna_estrategia_ciega_aprueba_h02_a_h05():
    assert estrategias_ciegas(SETS, DECISIONS) == []


def test_la_longitud_y_la_posicion_de_la_correcta_no_la_revelan():
    """Longitudes distintas y a lo mas 1.5 veces la menor; la correcta no se concentra en una posicion."""
    for name, questions in SETS.items():
        cap = -(-len(questions) // 3)  # ceil(n/3)
        by_slot = {}
        for q in questions:
            sizes = [len(o["label"]) for o in q["options"]]
            assert len(set(sizes)) == len(sizes), (q["key"], "empate de longitud", sizes)
            assert max(sizes) <= 1.5 * min(sizes), (q["key"], sizes)
            at = next(i for i, o in enumerate(q["options"]) if o["correct"])
            by_slot[at] = by_slot.get(at, 0) + 1
        assert max(by_slot.values()) <= cap, (name, "posición de la correcta", by_slot, cap)
