"""Recorridos esperados de DEMO-BECAS, calculados a mano en demo/recorridos-esperados.md (T-13).

Cada paso: (nodo, alternativa, razones, valores (privacy, access, quality) tras decidir,
justificación correcta).
"""

VARIABLES = ("privacy", "access", "quality")
ALL_CAUSES = ("D1", "D2", "D3", "D4", "D5", "D6")
EV_ACCESS = "Aviso: solicitudes incompletas"
EV_LEAK = "Aviso: datos visibles para otras personas"

RECORRIDOS = {
    "OUT_SOLID": {
        "steps": [
            ("D1", "d1a", ["r1a"], (7, 5, 5), True),
            ("D2", "d2a", [], (9, 5, 6), None),
            ("D3", "d3b", ["r3a"], (9, 7, 7), True),
            ("D4", "d4b", [], (9, 7, 8), None),
            ("D5", "d5b", ["r5a", "r5b"], (9, 8, 9), True),
            ("D6", "d6b", [], (10, 9, 10), None),
            ("D7", "d7b", ["r7a"], (10, 9, 10), True),
            ("D8", "d8b", ["r8a"], (10, 9, 10), True),
        ],
        "activations": [("D8", "tr_solid", "transition", ALL_CAUSES)],
        "event_titles": [],
    },
    "OUT_MIXED": {
        "steps": [
            ("D1", "d1c", ["r1a", "r1b"], (6, 6, 5), True),
            ("D2", "d2c", [], (7, 6, 5), None),
            ("D3", "d3c", ["r3a"], (7, 7, 5), True),
            ("D4", "d4b", [], (7, 7, 6), None),
            ("D5", "d5c", ["r5a", "r5c"], (7, 7, 7), True),
            ("D6", "d6a", [], (5, 7, 8), None),
            ("D7", "d7c", ["r7a"], (4, 7, 8), True),
            ("D8", "d8b", ["r8a"], (6, 7, 8), True),
        ],
        "activations": [("D7", "ev_leak", "event", ("D1", "D2", "D6", "D7"))],
        "event_titles": [EV_LEAK],
    },
    "OUT_CRISIS": {
        "steps": [
            ("D1", "d1b", ["r1c"], (3, 5, 5), False),
            ("D2", "d2b", [], (0, 5, 5), None),
            ("D3", "d3a", ["r3a", "r3c"], (0, 3, 5), False),
            ("D4", "d4a", [], (0, 3, 3), None),
            ("D5", "d5a", ["r5a"], (0, 1, 2), False),
            ("D6", "d6c", [], (0, 1, 0), None),
            ("D7", "d7a", ["r7a"], (0, 1, 0), True),
            ("D8", "d8a", ["r8c"], (0, 1, 0), False),
        ],
        "activations": [
            ("D6", "ev_access", "event", ("D3", "D5")),
            ("D7", "ev_leak", "event", ("D1", "D2")),
            ("D8", "tr_crisis", "transition", ALL_CAUSES),
        ],
        "event_titles": [EV_ACCESS, EV_LEAK],
    },
}
