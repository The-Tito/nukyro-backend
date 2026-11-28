"""Inventario de rutas y su caso de acceso ajeno (T-19, ADR-008 §5 y §6).

Cada ruta de la API está aquí con su tipo. Una ruta nueva que no esté hace fallar
`tests/unit/test_inventario_rutas.py`; una escrita aquí entra sola en las pruebas de aislamiento,
de CSRF y de cuenta bloqueada (`tests/integration/test_aislamiento.py`).

- PUBLICA: sin identidad; no hay nada propio que proteger.
- ENTRADA: sin credenciales crea un participante nuevo y solo suyo; con ellas, usa el propio.
- PROPIA: el recurso es de quien llama y la ruta no recibe el id de otra persona. El caso de acceso
  ajeno es que cada quien ve lo suyo y nada más.
- SESION: lleva `session_id`; lo ajeno y lo inexistente dan 404.
"""

PUBLICA, ENTRADA, PROPIA, SESION = "publica", "entrada", "propia", "sesion"

ACCEPT = {"age_confirmed": True, "privacy_notice_version": "DEMO-1", "terms_version": "DEMO-1"}
SCENARIO = {"scenario_key": "DEMO-BECAS", "self_reported_first": True}
S = "/api/v1/sessions/{session_id}"

# (método, ruta) -> (tipo, cuerpo de una petición válida en forma). {question_key} y {option_key}
# se completan con los del pre-test de la sesión de quien consulta.
RUTAS = {
    ("GET", "/api/v1/health"): (PUBLICA, None),
    ("GET", "/api/v1/entry"): (PUBLICA, None),
    ("POST", "/api/v1/participants"): (ENTRADA, ACCEPT),
    ("GET", "/api/v1/sessions"): (PROPIA, None),
    ("POST", "/api/v1/sessions"): (PROPIA, SCENARIO),
    ("GET", "/api/v1/account"): (PROPIA, None),
    ("POST", "/api/v1/account/login"): (PROPIA, {}),
    ("GET", S): (SESION, None),
    ("POST", S + "/decisions"): (
        SESION,
        {"node_key": "D01", "option_key": "A", "reason_keys": []},
    ),
    ("POST", S + "/advance"): (SESION, {"from_node_key": "intro"}),
    ("GET", S + "/assessments/{kind}"): (SESION, None),
    ("PUT", S + "/assessments/{kind}/answers/{question_key}"): (
        SESION,
        {"option_key": "{option_key}"},
    ),
    ("POST", S + "/assessments/{kind}/submit"): (SESION, None),
    ("GET", S + "/survey"): (SESION, None),
    ("POST", S + "/survey"): (SESION, {"usefulness": 3}),
    ("GET", S + "/summary"): (SESION, None),
}


def rutas_de(tipo: str):
    return [(m, p) for (m, p), (t, _) in RUTAS.items() if t == tipo]
