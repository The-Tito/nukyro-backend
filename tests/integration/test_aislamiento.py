"""T-19: cada ruta tiene su caso de acceso ajeno, la escritura de origen ajeno se rechaza y la
cuenta bloqueada no usa ninguna (ADR-002 §6, ADR-008 §5 y §6, RNF-17).

Se recorre `tests/acceso.py`: una ruta nueva entra aquí sin escribir nada más (y sin inventario
falla `tests/unit/test_inventario_rutas.py`).
"""

import pytest
from acceso import ACCEPT, ENTRADA, PROPIA, RUTAS, SCENARIO, SESION, rutas_de

from .conftest import WRITE, bearer

SESSION_ROUTES = [(m, p) for (m, p), (t, _) in RUTAS.items() if t == SESION]
NON_PUBLIC = [(m, p) for (m, p), (t, _) in RUTAS.items() if t != "publica"]
WRITES = [(m, p) for (m, p) in NON_PUBLIC if m != "GET"]
WATCHED = (
    "session_steps",
    "session_variables",
    "session_decisions",
    "session_events",
    "assessment_attempts",
)


class Person:
    """Una persona con su cliente y sus credenciales: anónima (cookie) o con cuenta (token)."""

    def __init__(self, kind, new_client, mint):
        self.kind, self.client, self.token = kind, new_client(), None
        self.creds = {}
        if kind == "cuenta":
            self.token = mint()
            self.creds = bearer(self.token)
            self.client.post("/api/v1/account/login", json={}, headers={**WRITE, **self.creds})
        self.client.post("/api/v1/participants", json=ACCEPT, headers={**WRITE, **self.creds})

    def send(self, method, path, body=None, *, creds=None, headers=None):
        sent = {**WRITE, **(self.creds if creds is None else creds), **(headers or {})}
        return self.client.request(method, path, json=body, headers=sent)

    def start_session(self):
        response = self.send("POST", "/api/v1/sessions", SCENARIO)
        assert response.status_code == 201
        self.sid = response.json()["id"]
        first = self.send("GET", f"/api/v1/sessions/{self.sid}/assessments/pretest").json()
        question = first["questions"][0]
        self.keys = {
            "session_id": self.sid,
            "kind": "pretest",
            "question_key": question["key"],
            "option_key": question["options"][0]["key"],
        }
        return self


def fill(value, keys):
    if isinstance(value, str):
        return value.format(**keys) if "{" in value else value
    if isinstance(value, dict):
        return {k: fill(v, keys) for k, v in value.items()}
    return value


def call(person, method, template, creds=None, headers=None, victim=None):
    """`template` sobre la sesión de `victim` (o la propia), con las credenciales de `person`."""
    owner = victim or person
    path = fill(template, owner.keys)
    body = fill(RUTAS[(method, template)][1], owner.keys)
    return person.send(method, path, body, creds=creds, headers=headers)


def snapshot(db, person):
    """Todo lo de la sesión y su participante, con la actividad incluida."""
    sid = person.sid
    rows = [
        db.execute("SELECT to_jsonb(s) FROM nukyro.sessions s WHERE id = %s", (sid,)).fetchall(),
        db.execute(
            "SELECT to_jsonb(p) FROM nukyro.participants p "
            "WHERE id = (SELECT participant_id FROM nukyro.sessions WHERE id = %s)",
            (sid,),
        ).fetchall(),
        db.execute("SELECT count(*) FROM nukyro.survey_responses").fetchall(),
    ]
    for table in WATCHED:
        rows.append(
            db.execute(
                f"SELECT count(*) FROM nukyro.{table} WHERE session_id = %s", (sid,)
            ).fetchall()
        )
    rows.append(
        db.execute(
            "SELECT count(*) FROM nukyro.assessment_answers a JOIN nukyro.assessment_attempts t "
            "ON t.id = a.attempt_id WHERE t.session_id = %s",
            (sid,),
        ).fetchall()
    )
    return rows


@pytest.fixture(params=["anonimo", "cuenta"])
def victim(request, new_client, mint):
    return Person(request.param, new_client, mint).start_session()


@pytest.fixture(params=["anonimo", "cuenta"])
def attacker(request, new_client, mint):
    return Person(request.param, new_client, mint)


@pytest.mark.parametrize(("method", "template"), SESSION_ROUTES)
def test_t19_lo_ajeno_da_404_y_no_cambia_nada(victim, attacker, superuser, method, template):
    before = snapshot(superuser, victim)
    foreign = call(attacker, method, template, victim=victim)
    assert foreign.status_code == 404, (method, template, foreign.text)
    assert snapshot(superuser, victim) == before
    # la misma petición hecha por su dueño sí llega a la sesión: el 404 era por ser ajena
    own = call(victim, method, template)
    assert own.status_code != 404, (method, template, own.status_code, own.text)


@pytest.mark.parametrize(("method", "template"), SESSION_ROUTES)
def test_t19_lo_inexistente_da_el_mismo_404_que_lo_ajeno(victim, method, template):
    ghost = "00000000-0000-4000-8000-000000000000"
    path = fill(template, {**victim.keys, "session_id": ghost})
    body = fill(RUTAS[(method, template)][1], victim.keys)
    missing = victim.send(method, path, body)
    foreign_like = victim.send(
        method, fill(template, {**victim.keys, "session_id": "no-es-uuid"}), body
    )
    assert missing.status_code == foreign_like.status_code == 404
    assert missing.json() == foreign_like.json()


AUTHENTICATED = [(m, p) for (m, p) in NON_PUBLIC if (m, p) not in rutas_de(ENTRADA)]


def test_t19_sin_credenciales_la_entrada_crea_un_participante_nuevo_y_no_toca_a_nadie(
    victim, new_client, superuser
):
    before = snapshot(superuser, victim)
    fresh = new_client()
    response = fresh.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
    assert response.status_code == 201
    assert fresh.get("/api/v1/sessions").json() == {"sessions": []}  # es otro participante
    assert snapshot(superuser, victim) == before


@pytest.mark.parametrize(("method", "template"), AUTHENTICATED)
def test_t19_sin_credenciales_es_401_y_no_escribe(victim, new_client, superuser, method, template):
    before = snapshot(superuser, victim)
    path = fill(template, victim.keys)
    body = fill(RUTAS[(method, template)][1], victim.keys)
    response = new_client().request(method, path, json=body, headers=WRITE)  # sin cookie ni token
    assert response.status_code == 401, (method, template, response.text)
    assert snapshot(superuser, victim) == before


@pytest.mark.parametrize(("method", "template"), WRITES)
@pytest.mark.parametrize(
    "bad",
    [
        {"Origin": "https://otro.example.test"},
        {"Origin": "null"},
        {"X-Nukyro-Request": "0"},
        {"X-Nukyro-Request": ""},
    ],
    ids=["origen-ajeno", "origen-null", "cabecera-en-0", "cabecera-vacia"],
)
def test_t19_una_escritura_de_origen_ajeno_se_rechaza_con_las_credenciales_del_dueno(
    victim, superuser, method, template, bad
):
    before = snapshot(superuser, victim)
    response = call(victim, method, template, headers=bad)
    assert response.status_code == 403, (method, template, response.text)
    assert snapshot(superuser, victim) == before


@pytest.mark.parametrize(("method", "template"), WRITES)
@pytest.mark.parametrize("missing", ["Origin", "X-Nukyro-Request"])
def test_t19_una_escritura_sin_origen_o_sin_cabecera_se_rechaza(
    victim, superuser, method, template, missing
):
    before = snapshot(superuser, victim)
    path = fill(template, victim.keys)
    body = fill(RUTAS[(method, template)][1], victim.keys)
    headers = {k: v for k, v in WRITE.items() if k != missing}
    response = victim.client.request(method, path, json=body, headers={**headers, **victim.creds})
    assert response.status_code == 403, (method, template, response.text)
    assert snapshot(superuser, victim) == before


@pytest.mark.parametrize(("method", "template"), NON_PUBLIC)
def test_t19_una_cuenta_bloqueada_no_usa_ninguna_ruta(
    new_client, mint, superuser, method, template
):
    person = Person("cuenta", new_client, mint).start_session()
    account = superuser.execute(
        "SELECT a.id FROM nukyro.accounts a JOIN nukyro.participants p ON p.account_id = a.id "
        "JOIN nukyro.sessions s ON s.participant_id = p.id WHERE s.id = %s",
        (person.sid,),
    ).fetchone()[0]
    superuser.execute(
        "SELECT nukyro.block_account(%s, 'user_request', now() + interval '1 day')", (account,)
    )
    before = snapshot(superuser, person)
    response = call(person, method, template)
    assert response.status_code == 403, (method, template, response.text)
    assert response.json()["error"]["code"] == "account_blocked"
    assert snapshot(superuser, person) == before


def test_t19_las_rutas_propias_solo_devuelven_lo_de_quien_llama(new_client, mint):
    a = Person("cuenta", new_client, mint).start_session()
    b = Person("cuenta", new_client, mint)
    assert [s["id"] for s in a.send("GET", "/api/v1/sessions").json()["sessions"]] == [a.sid]
    assert b.send("GET", "/api/v1/sessions").json() == {"sessions": []}
    assert (
        a.send("GET", "/api/v1/account").json()["email"]
        != b.send("GET", "/api/v1/account").json()["email"]
    )
    anon = Person("anonimo", new_client, mint)
    assert anon.send("GET", "/api/v1/sessions").json() == {"sessions": []}
    assert [r for r in RUTAS if RUTAS[r][0] == PROPIA]  # el inventario las declara


# ---- La excepción de los GET (ADR-008 §6): solo renuevan last_activity_at ----


@pytest.mark.parametrize(
    "template",
    [p for m, p in SESSION_ROUTES if m == "GET"] + ["/api/v1/sessions"],
)
def test_t19_un_get_autenticado_solo_renueva_la_actividad(victim, superuser, template):
    """Un enlace externo puede renovar la fecha de actividad, pero no leer ni cambiar otra cosa."""

    def inert(person):
        rows = snapshot(superuser, person)
        # fuera la actividad: lo único que un GET puede mover
        return [
            [{k: v for k, v in r[0].items() if k != "last_activity_at"} for r in rows[0]],
            [{k: v for k, v in r[0].items() if k != "last_activity_at"} for r in rows[1]],
            *rows[2:],
        ]

    before = inert(victim)
    response = call(victim, "GET", template)
    assert response.status_code in (200, 409)
    assert inert(victim) == before


def test_t19_las_respuestas_no_se_pueden_leer_desde_otro_origen(victim):
    """Sin CORS ninguna página ajena lee la respuesta aunque el navegador envíe la cookie."""
    response = victim.send(
        "GET", "/api/v1/sessions", headers={"Origin": "https://otro.example.test"}
    )
    assert not any(h.lower().startswith("access-control-") for h in response.headers)
    preflight = victim.client.options(
        "/api/v1/sessions",
        headers={"Origin": "https://otro.example.test", "Access-Control-Request-Method": "POST"},
    )
    assert preflight.status_code in (403, 404, 405)
    assert not any(h.lower().startswith("access-control-") for h in preflight.headers)
