"""Recorridos esperados de DEMO-BECAS, calculados a mano en demo/recorridos-esperados.md (T-13).

Cada paso: (nodo, alternativa, razones, valores (privacy, access, quality) tras decidir,
justificación correcta).
"""

VARIABLES = ("privacy", "access", "quality")
ALL_CAUSES = ("D1", "D2", "D3", "D4", "D5", "D6")
EV_ACCESS = "Aviso: acceso bajo"
EV_LEAK = "Aviso: protección de datos baja"

RECORRIDOS = {
    "OUT_SOLID": {
        "steps": [
            ("D1", "o1_2923", ["r1_d6f7"], (7, 5, 5), True),
            ("D2", "o2_c749", [], (9, 5, 6), None),
            ("D3", "o3_a1b4", ["r3_973e"], (9, 7, 7), True),
            ("D4", "o4_65c3", [], (9, 7, 8), None),
            ("D5", "o5_7d70", ["r5_3139", "r5_7131"], (9, 8, 9), True),
            ("D6", "o6_701b", [], (10, 9, 10), None),
            ("D7", "o7_34d2", ["r7_06fc"], (10, 9, 10), True),
            ("D8", "o8_d43a", ["r8_26f4"], (10, 9, 10), True),
        ],
        "activations": [("D8", "tr_solid", "transition", ALL_CAUSES)],
        "event_titles": [],
    },
    "OUT_MIXED": {
        "steps": [
            ("D1", "o1_5a9a", ["r1_d6f7", "r1_b591"], (6, 6, 5), True),
            ("D2", "o2_2a86", [], (7, 6, 5), None),
            ("D3", "o3_509f", ["r3_973e"], (7, 7, 5), True),
            ("D4", "o4_65c3", [], (7, 7, 6), None),
            ("D5", "o5_b24e", ["r5_3139", "r5_cc31"], (7, 7, 7), True),
            ("D6", "o6_ed23", [], (5, 7, 8), None),
            ("D7", "o7_485f", ["r7_06fc"], (4, 7, 8), True),
            ("D8", "o8_d43a", ["r8_26f4"], (6, 7, 8), True),
        ],
        "activations": [("D7", "ev_leak", "event", ("D1", "D2", "D6", "D7"))],
        "event_titles": [EV_LEAK],
    },
    "OUT_CRISIS": {
        "steps": [
            ("D1", "o1_1fba", ["r1_948b"], (3, 5, 5), False),
            ("D2", "o2_808f", [], (0, 5, 5), None),
            ("D3", "o3_9a36", ["r3_973e", "r3_7688"], (0, 3, 5), False),
            ("D4", "o4_19ff", [], (0, 3, 3), None),
            ("D5", "o5_2565", ["r5_3139"], (0, 1, 2), False),
            ("D6", "o6_9abb", [], (0, 1, 0), None),
            ("D7", "o7_b8f2", ["r7_06fc"], (0, 1, 0), True),
            ("D8", "o8_0923", ["r8_f273"], (0, 1, 0), False),
        ],
        "activations": [
            ("D6", "ev_access", "event", ("D3", "D5")),
            ("D7", "ev_leak", "event", ("D1", "D2")),
            ("D8", "tr_crisis", "transition", ALL_CAUSES),
        ],
        "event_titles": [EV_ACCESS, EV_LEAK],
    },
}
