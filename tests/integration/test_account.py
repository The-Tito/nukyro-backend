"""Cuenta, vinculación y aislamiento con token, contra la API y la base reales (T-18, T-19).

RF-074 a RF-077, defectos 9 y 12. El emisor simulado firma los tokens (D-34).
"""

import threading

import pytest

from .conftest import ACCEPT, WRITE, bearer

SCENARIO = {"scenario_key": "DEMO-BECAS", "self_reported_first": True}


def cookie(value):
    """La cookie anónima como cabecera (el jar de httpx no casa con el host `localhost`)."""
    return {"Cookie": f"__Host-nukyro_participant={value}"}


def login(client, token, *, body=None, extra=None):
    headers = {**WRITE, **bearer(token), **(extra or {})}
    return client.post("/api/v1/account/login", json=body or {}, headers=headers)


def accept(client, token):
    return client.post("/api/v1/participants", json=ACCEPT, headers={**WRITE, **bearer(token)})


def start(client, token):
    return client.post("/api/v1/sessions", json=SCENARIO, headers={**WRITE, **bearer(token)})


def sessions(client, token):
    return client.get("/api/v1/sessions", headers=bearer(token))


def account_row(db, sub):
    return db.execute(
        "SELECT id, email, nickname, newsletter_opt_in, surveys_opt_in, status "
        "FROM nukyro.accounts WHERE cognito_sub = %s",
        (sub,),
    ).fetchone()


def sub_of(mint_token) -> str:
    import jwt

    return jwt.decode(mint_token, options={"verify_signature": False})["sub"]


# ------------------------------ RF-074: crear la cuenta ------------------------------


def test_rf074_el_primer_inicio_crea_la_cuenta_con_las_casillas_sin_marcar(
    new_client, mint, superuser
):
    token = mint(nickname="Ana")
    response = login(new_client(), token)
    assert response.status_code == 200
    assert response.json() == {"nickname": "Ana", "has_participant": False, "linked": False}
    acc = account_row(superuser, sub_of(token))
    assert acc[2:] == ("Ana", False, False, "active")
    events = superuser.execute(
        "SELECT consent_type, granted, source FROM nukyro.consent_events WHERE account_id = %s "
        "ORDER BY consent_type",
        (acc[0],),
    ).fetchall()
    assert events == [("newsletter", False, "registration"), ("surveys", False, "registration")]


def test_rf074_las_casillas_marcadas_se_guardan_y_quedan_en_el_historial(
    new_client, mint, superuser
):
    token = mint()
    body = {"newsletter_opt_in": True, "surveys_opt_in": True}
    assert login(new_client(), token, body=body).status_code == 200
    acc = account_row(superuser, sub_of(token))
    assert acc[3:5] == (True, True)
    granted = superuser.execute(
        "SELECT count(*) FROM nukyro.consent_events WHERE account_id = %s AND granted", (acc[0],)
    ).fetchone()[0]
    assert granted == 2


def test_rf074_repetir_el_inicio_no_duplica_ni_cambia_las_casillas(new_client, mint, superuser):
    token = mint()
    client = new_client()
    login(client, token, body={"newsletter_opt_in": True})
    again = login(client, token, body={"newsletter_opt_in": False, "surveys_opt_in": True})
    assert again.status_code == 200
    sub = sub_of(token)
    assert superuser.execute(
        "SELECT count(*) FROM nukyro.accounts WHERE cognito_sub = %s", (sub,)
    ).fetchone() == (1,)
    acc = account_row(superuser, sub)
    assert acc[3:5] == (True, False)  # las casillas del registro no se reescriben al iniciar
    assert superuser.execute(
        "SELECT count(*) FROM nukyro.consent_events WHERE account_id = %s", (acc[0],)
    ).fetchone() == (2,)


def test_rf074_el_nickname_no_es_unico(new_client, mint, superuser):
    for _ in range(2):
        assert login(new_client(), mint(nickname="Repetido")).status_code == 200
    n = superuser.execute(
        "SELECT count(*) FROM nukyro.accounts WHERE nickname = 'Repetido'"
    ).fetchone()[0]
    assert n >= 2


def test_rf074_el_correo_y_el_nickname_se_sincronizan_con_cognito(new_client, mint, superuser):
    sub = "sub-sync-" + mint()[-12:]
    login(new_client(), mint(sub=sub, email="viejo@example.test", nickname="Viejo"))
    login(new_client(), mint(sub=sub, email="nuevo@example.test", nickname="Nuevo"))
    assert account_row(superuser, sub)[1:3] == ("nuevo@example.test", "Nuevo")


def test_rf074_sin_correo_verificado_no_se_crea_la_cuenta(new_client, mint, superuser):
    token = mint(email_verified=False)
    assert login(new_client(), token).status_code == 403
    assert account_row(superuser, sub_of(token)) is None


@pytest.mark.parametrize(
    "spec",
    [{"omit": ["nickname"]}, {"nickname": ""}, {"nickname": "x" * 41}, {"omit": ["email"]}],
)
def test_rf074_un_token_sin_correo_o_nickname_validos_no_crea_cuenta(
    new_client, mint, superuser, spec
):
    token = mint(**spec)
    assert login(new_client(), token).status_code == 422
    assert account_row(superuser, sub_of(token)) is None


def test_rf074_el_cuerpo_rechaza_campos_desconocidos(new_client, mint, superuser):
    token = mint()
    assert login(new_client(), token, body={"is_admin": True}).status_code == 422
    assert account_row(superuser, sub_of(token)) is None


def test_rf074_los_inicios_simultaneos_dejan_una_cuenta_y_un_participante(
    new_client, mint, superuser
):
    token = mint()
    results = []

    def go():
        client = new_client()
        results.append(login(client, token).status_code)

    threads = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results == [200] * 4
    assert superuser.execute(
        "SELECT count(*) FROM nukyro.accounts WHERE cognito_sub = %s", (sub_of(token),)
    ).fetchone() == (1,)


# ------------------------- tokens y cookie: quién puede qué -------------------------


@pytest.mark.parametrize(
    ("spec", "status"),
    [
        ({"signing": "forged"}, 401),
        ({"signing": "unknown_kid"}, 401),
        ({"iss": "https://otro.example.test"}, 401),
        ({"aud": "otro"}, 401),
        ({"token_use": "access"}, 401),
        ({"iat_offset": -4000}, 401),
        ({"lifetime": 7200}, 401),
        ({"groups": ["admins"]}, 403),
    ],
)
def test_rf075_un_token_invalido_no_abre_ninguna_ruta(new_client, mint, superuser, spec, status):
    token = mint(**spec)
    client = new_client()
    assert login(client, token).status_code == status
    assert sessions(client, token).status_code == status
    assert accept(client, token).status_code == status
    assert account_row(superuser, sub_of(token)) is None


@pytest.mark.parametrize("header", ["", "Bearer", "Basic abc", "Bearer a.b.c"])
def test_rf075_un_encabezado_malo_es_401_y_no_cae_a_la_cookie(person, header):
    """Con Authorization presente nunca se usa la cookie, aunque sea válida."""
    response = person.get("/api/v1/sessions", headers={"Authorization": header})
    assert response.status_code == 401


def test_rf075_las_rutas_de_cuenta_no_aceptan_la_cookie(person):
    assert person.post("/api/v1/account/login", json={}, headers=WRITE).status_code == 401
    assert person.get("/api/v1/account").status_code == 401


def test_rf075_get_account_devuelve_lo_de_quien_pregunta(new_client, mint):
    token = mint(nickname="Luz", email="luz@example.test")
    client = new_client()
    login(client, token, body={"surveys_opt_in": True})
    got = client.get("/api/v1/account", headers=bearer(token))
    assert got.status_code == 200
    assert got.json() == {
        "nickname": "Luz",
        "email": "luz@example.test",
        "newsletter_opt_in": False,
        "surveys_opt_in": True,
    }


def test_rf075_sin_haber_iniciado_sesion_la_cuenta_no_existe(new_client, mint):
    token = mint()
    client = new_client()
    assert client.get("/api/v1/account", headers=bearer(token)).status_code == 401
    assert sessions(client, token).status_code == 401  # no se crea sola por usar otra ruta


def test_rf062_la_escritura_con_token_exige_origin_y_cabecera(new_client, mint):
    token = mint()
    client = new_client()
    assert client.post("/api/v1/account/login", json={}, headers=bearer(token)).status_code == 403
    cross = {**WRITE, "Origin": "https://otro.example.test", **bearer(token)}
    assert client.post("/api/v1/account/login", json={}, headers=cross).status_code == 403


# --------------------- RF-075: con cuenta, desde cualquier dispositivo ---------------------


def test_rf075_la_cuenta_acepta_documentos_inicia_sesion_y_la_reanuda_desde_otro_dispositivo(
    new_client, mint
):
    token = mint()
    phone = new_client()
    assert login(phone, token).json()["has_participant"] is False
    created = accept(phone, token)
    assert created.status_code == 201
    assert "set-cookie" not in created.headers  # con cuenta no hay cookie que entregar
    assert login(phone, token).json()["has_participant"] is True
    session = start(phone, token)
    assert session.status_code == 201
    laptop = new_client()  # otro dispositivo: sin cookie, solo el token
    listed = sessions(laptop, token)
    assert [s["id"] for s in listed.json()["sessions"]] == [session.json()["id"]]
    assert (
        laptop.get(f"/api/v1/sessions/{session.json()['id']}", headers=bearer(token)).status_code
        == 200
    )


def test_rf075_aceptar_dos_veces_no_crea_otro_participante(new_client, mint, superuser):
    token = mint()
    client = new_client()
    login(client, token)
    assert accept(client, token).status_code == 201
    assert accept(client, token).status_code == 200
    n = superuser.execute(
        "SELECT count(*) FROM nukyro.participants p JOIN nukyro.accounts a ON a.id = p.account_id "
        "WHERE a.cognito_sub = %s",
        (sub_of(token),),
    ).fetchone()[0]
    assert n == 1


def test_rf075_una_cuenta_sin_documentos_aceptados_no_inicia_sesion(new_client, mint):
    token = mint()
    client = new_client()
    login(client, token)
    response = start(client, token)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "documents_required"


def test_t19_una_cuenta_no_ve_ni_toca_la_sesion_de_otra(new_client, mint):
    owner, intruder = mint(), mint()
    client = new_client()
    for token in (owner, intruder):
        login(client, token)
        accept(client, token)
    sid = start(client, owner).json()["id"]
    for method, path, body in (
        ("get", f"/api/v1/sessions/{sid}", None),
        ("post", f"/api/v1/sessions/{sid}/advance", {"from_node_key": "intro"}),
        ("get", f"/api/v1/sessions/{sid}/summary", None),
        ("get", f"/api/v1/sessions/{sid}/survey", None),
    ):
        kwargs = (
            {"json": body, "headers": {**WRITE, **bearer(intruder)}}
            if body is not None
            else {"headers": bearer(intruder)}
        )
        assert getattr(client, method)(path, **kwargs).status_code == 404, path
    assert sessions(client, intruder).json() == {"sessions": []}


def test_t19_con_token_y_cookie_manda_el_token(new_client, mint):
    """Con cookie de una sesión anónima y el token de otra cuenta, se ve lo de la cuenta."""
    anon, _sid = anonymous_with_session(new_client)
    token = mint()
    other = new_client()
    login(other, token)
    accept(other, token)
    assert sessions(anon, token).json() == {"sessions": []}
    assert len(anon.get("/api/v1/sessions").json()["sessions"]) == 1  # sin token, sigue lo suyo


# ------------------------ RF-076 y defecto 9: vincular el progreso ------------------------


def anonymous_with_session(new_client):
    client = new_client()
    assert client.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
    sid = client.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).json()["id"]
    return client, sid


def test_rf076_crear_la_cuenta_conserva_el_progreso_e_invalida_la_cookie(new_client, mint):
    anon, sid = anonymous_with_session(new_client)
    old_cookie = anon.cookies.get("__Host-nukyro_participant")
    token = mint()
    response = login(anon, token)
    assert response.status_code == 200
    assert response.json()["linked"] is True and response.json()["has_participant"] is True
    assert "max-age=0" in response.headers["set-cookie"].lower()
    # la sesión es de la cuenta
    laptop = new_client()
    assert [s["id"] for s in sessions(laptop, token).json()["sessions"]] == [sid]
    # el secreto anterior ya no sirve, ni siquiera reenviándolo a mano
    assert laptop.get("/api/v1/sessions", headers=cookie(old_cookie)).status_code == 401


def test_rf076_repetir_el_inicio_con_la_misma_cookie_no_cambia_nada(new_client, mint):
    anon, sid = anonymous_with_session(new_client)
    stale = anon.cookies.get("__Host-nukyro_participant")
    token = mint()
    login(anon, token)
    other = new_client()
    again = login(other, token, extra=cookie(stale))
    assert again.status_code == 200 and again.json()["linked"] is False
    assert [s["id"] for s in sessions(other, token).json()["sessions"]] == [sid]


def test_defecto9_la_cuenta_con_progreso_y_un_navegador_con_progreso_dejan_una_primera_sesion(
    new_client, mint
):
    token = mint()
    app_client = new_client()
    login(app_client, token)
    accept(app_client, token)
    first = start(app_client, token).json()["id"]  # la más antigua, con la cuenta
    anon, second = anonymous_with_session(new_client)  # después, en un navegador sin cuenta
    assert login(anon, token).json()["linked"] is True
    listed = {s["id"]: s for s in sessions(new_client(), token).json()["sessions"]}
    assert set(listed) == {first, second}
    assert listed[first]["is_first_session"] is True
    assert listed[second]["is_first_session"] is False
    assert sum(s["is_first_session"] for s in listed.values()) == 1


def test_defecto9_si_la_sesion_del_navegador_es_mas_antigua_ella_es_la_primera(new_client, mint):
    anon, older = anonymous_with_session(new_client)  # primero, sin cuenta
    token = mint()
    other = new_client()
    login(other, token)
    accept(other, token)
    newer = start(other, token).json()["id"]
    assert login(anon, token).json()["linked"] is True
    listed = {s["id"]: s for s in sessions(new_client(), token).json()["sessions"]}
    assert listed[older]["is_first_session"] is True
    assert listed[newer]["is_first_session"] is False


def test_defecto9_las_vinculaciones_simultaneas_dejan_una_sola_primera_sesion(
    new_client, mint, superuser
):
    token = mint()
    base = new_client()
    login(base, token)
    accept(base, token)
    start(base, token)
    cookies = []
    for _ in range(3):
        anon, _sid = anonymous_with_session(new_client)
        cookies.append(anon.cookies.get("__Host-nukyro_participant"))
    statuses = []

    def go(value):
        statuses.append(login(new_client(), token, extra=cookie(value)).status_code)

    threads = [threading.Thread(target=go, args=(c,)) for c in cookies * 2]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert statuses == [200] * 6
    listed = sessions(new_client(), token).json()["sessions"]
    assert len(listed) == 4
    assert sum(s["is_first_session"] for s in listed) == 1


def test_rf076_la_cookie_de_otra_cuenta_no_se_vincula_a_quien_no_es_su_dueno(new_client, mint):
    """El secreto de un participante que ya tiene cuenta no existe: no se puede robar progreso."""
    owner = mint()
    client = new_client()
    login(client, owner)
    accept(client, owner)
    start(client, owner)
    thief = mint()
    response = login(client, thief)  # sin cookie con secreto: nada que vincular
    assert response.json()["linked"] is False
    assert sessions(client, thief).status_code == 409  # sin documentos propios
    assert len(sessions(client, owner).json()["sessions"]) == 1


# ------------------------------ cuenta bloqueada (D-20) ------------------------------


def block(superuser, token, due="now() + interval '1 day'"):
    acc = account_row(superuser, sub_of(token))
    superuser.execute(f"SELECT nukyro.block_account(%s, 'user_request', {due})", (acc[0],))


def test_d20_una_cuenta_bloqueada_no_inicia_sesion_ni_usa_ninguna_ruta(new_client, mint, superuser):
    token = mint()
    client = new_client()
    login(client, token)
    accept(client, token)
    block(superuser, token)
    for response in (
        login(client, token),
        accept(client, token),
        sessions(client, token),
        start(client, token),
        client.get("/api/v1/account", headers=bearer(token)),
    ):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "account_blocked"


def test_d20_vincular_a_una_cuenta_bloqueada_no_mueve_el_progreso(new_client, mint, superuser):
    token = mint()
    login(new_client(), token)
    block(superuser, token)
    anon, sid = anonymous_with_session(new_client)
    assert login(anon, token).status_code == 403
    assert anon.get("/api/v1/sessions").status_code == 200  # el navegador conserva lo suyo
    assert anon.get("/api/v1/sessions").json()["sessions"][0]["id"] == sid
