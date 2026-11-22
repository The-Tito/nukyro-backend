"""Evaluaciones de DEMO-BECAS para la caja negra (T-14): clave de respuestas y puntuaciones a mano.

La clave es un dato de prueba (la caja negra no lee el escenario): la opción correcta de cada
pregunta según demo/scenario-becas.json. Cada recorrido responde con aciertos y fallos elegidos; el
porcentaje esperado se calculó a mano como correctas / respondidas * 100, a dos decimales.
"""

CLAVE = {
    "pretest": {"pre1": "b", "pre2": "a", "pre3": "c", "pre4": "c", "pre5": "b", "pre6": "a"},
    "posttest": {
        "post1": "c",
        "post2": "a",
        "post3": "b",
        "post4": "a",
        "post5": "b",
        "post6": "a",
    },
    "transfer": {"tra1": "a", "tra2": "a", "tra3": "b", "tra4": "b", "tra5": "c"},
    "causal": {"cau1": "c", "cau2": "a", "cau3": "c", "cau4": "b", "cau5": "a"},
}
ORDEN_FINAL = ("posttest", "transfer", "causal")

# Causales que ocurren en cada recorrido (RF-058): eventos activados y el desenlace alcanzado.
CAUSALES = {
    "OUT_SOLID": ["cau3"],
    "OUT_MIXED": ["cau2", "cau4"],
    "OUT_CRISIS": ["cau1", "cau2", "cau5"],
}

# (respuestas, puntuación esperada). Los fallos están marcados con «x».
EVALUACIONES = {
    "OUT_SOLID": {
        # pre1 b, pre3 c aciertan; pre2, pre4, pre5, pre6 fallan: 2/6
        "pretest": (
            {"pre1": "b", "pre2": "b", "pre3": "c", "pre4": "a", "pre5": "a", "pre6": "c"},
            33.33,
        ),
        # 6/6
        "posttest": (
            {"post1": "c", "post2": "a", "post3": "b", "post4": "a", "post5": "b", "post6": "a"},
            100.0,
        ),
        # tra5 falla: 4/5
        "transfer": ({"tra1": "a", "tra2": "a", "tra3": "b", "tra4": "b", "tra5": "a"}, 80.0),
        # solo cau3: 1/1
        "causal": ({"cau3": "c"}, 100.0),
    },
    "OUT_MIXED": {
        # pre2, pre4, pre5, pre6 aciertan: 4/6
        "pretest": (
            {"pre1": "a", "pre2": "a", "pre3": "a", "pre4": "c", "pre5": "b", "pre6": "a"},
            66.67,
        ),
        # post4 y post6 fallan: 4/6
        "posttest": (
            {"post1": "c", "post2": "a", "post3": "b", "post4": "b", "post5": "b", "post6": "c"},
            66.67,
        ),
        # tra2 y tra4 fallan: 3/5
        "transfer": ({"tra1": "a", "tra2": "b", "tra3": "b", "tra4": "a", "tra5": "c"}, 60.0),
        # cau2 acierta, cau4 falla: 1/2
        "causal": ({"cau2": "a", "cau4": "a"}, 50.0),
    },
    "OUT_CRISIS": {
        # todas fallan: 0/6, puntúa 0.00 (respondió las seis)
        "pretest": (
            {"pre1": "a", "pre2": "b", "pre3": "a", "pre4": "b", "pre5": "c", "pre6": "b"},
            0.0,
        ),
        # solo post1 falla: 5/6
        "posttest": (
            {"post1": "a", "post2": "a", "post3": "b", "post4": "a", "post5": "b", "post6": "a"},
            83.33,
        ),
        # tra2 y tra4 aciertan: 2/5
        "transfer": ({"tra1": "b", "tra2": "a", "tra3": "a", "tra4": "b", "tra5": "a"}, 40.0),
        # cau1 y cau5 aciertan, cau2 falla: 2/3
        "causal": ({"cau1": "c", "cau2": "b", "cau5": "a"}, 66.67),
    },
}
