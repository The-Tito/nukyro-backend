"""Caja negra de la cuenta (T-18, T-19): solo HTTPS y el emisor simulado, sin la aplicación.

RF-074 a RF-077. El emisor simulado (D-34) firma los tokens; la API los verifica con su JWKS.
"""

import os
import uuid

import httpx
import pytest
from test_entry import ACCEPT, SCENARIO, WRITE, new_client

ISSUER_URL = os.environ["NUKYRO_ISSUER_URL"]
COOKIE = "__Host-nukyro_participant"


def mint(**spec) -> str:
    spec.setdefault("sub", f"sub-{uuid.uuid4().hex}")
    spec.setdefault("email", f"{uuid.uuid4().hex[:12]}@example.test")
    response = httpx.post(f"{ISSUER_URL}/token", json=spec, timeout=10)
    response.raise_for_status()
    return response.json()["id_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client, token, body=None):
    return client.post("/api/v1/account/login", json=body or {}, headers={**WRITE, **bearer(token)})


def test_rf074_rf075_crear_la_cuenta_aceptar_iniciar_y_reanudar_desde_otro_dispositivo():
    token = mint(nickname="Marta")
    with new_client() as phone, new_client() as laptop:
        first = login(phone, token)
        assert first.status_code == 200
        assert first.json() == {"nickname": "Marta", "has_participant": False, "linked": False}
        accepted = phone.post(
            "/api/v1/participants", json=ACCEPT, headers={**WRITE, **bearer(token)}
        )
        assert accepted.status_code == 201 and COOKIE not in phone.cookies
        started = phone.post("/api/v1/sessions", json=SCENARIO, headers={**WRITE, **bearer(token)})
        assert started.status_code == 201
        listed = laptop.get("/api/v1/sessions", headers=bearer(token))  # sin cookie
        assert [s["id"] for s in listed.json()["sessions"]] == [started.json()["id"]]


@pytest.mark.parametrize(
    ("spec", "status"),
    [
        ({"signing": "forged"}, 401),
        ({"signing": "unknown_kid"}, 401),
        ({"iss": "https://otro.example.test"}, 401),
        ({"aud": "otro"}, 401),
        ({"token_use": "access"}, 401),
        ({"iat_offset": -4000}, 401),
        ({"groups": ["admins"]}, 403),
        ({"email_verified": False}, 403),
    ],
)
def test_rf074_un_token_invalido_o_sin_correo_verificado_no_entra(spec, status):
    token = mint(**spec)
    with new_client() as client:
        assert login(client, token).status_code == status
        assert client.get("/api/v1/sessions", headers=bearer(token)).status_code in (401, 403)


def test_rf075_sin_token_ni_cookie_no_hay_acceso():
    with new_client() as client:
        assert client.get("/api/v1/sessions").status_code == 401
        assert client.get("/api/v1/account").status_code == 401
        assert client.post("/api/v1/account/login", json={}, headers=WRITE).status_code == 401


def test_rf076_crear_la_cuenta_conserva_el_progreso_y_la_cookie_deja_de_servir():
    with new_client() as anon:
        assert anon.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
        sid = anon.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).json()["id"]
        old = anon.cookies.get(COOKIE)
        token = mint()
        done = login(anon, token)
        assert done.json()["linked"] is True
        with new_client() as laptop:
            listed = laptop.get("/api/v1/sessions", headers=bearer(token))
            assert [s["id"] for s in listed.json()["sessions"]] == [sid]
            stale = {"Cookie": f"{COOKIE}={old}"}  # el jar de httpx no sirve con `localhost`
            assert laptop.get("/api/v1/sessions", headers=stale).status_code == 401


def test_rf077_rf076_dos_primeras_sesiones_se_vuelven_una_al_vincular():
    token = mint()
    with new_client() as app_client, new_client() as anon:
        login(app_client, token)
        headers = {**WRITE, **bearer(token)}
        app_client.post("/api/v1/participants", json=ACCEPT, headers=headers)
        first = app_client.post("/api/v1/sessions", json=SCENARIO, headers=headers).json()["id"]
        anon.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
        second = anon.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).json()["id"]
        login(anon, token)
        listed = {
            s["id"]: s["is_first_session"]
            for s in app_client.get("/api/v1/sessions", headers=bearer(token)).json()["sessions"]
        }
        assert listed == {first: True, second: False}


def test_t19_la_sesion_de_otra_cuenta_es_404_y_la_escritura_ajena_es_403():
    owner, intruder = mint(), mint()
    with new_client() as client:
        for token in (owner, intruder):
            login(client, token)
            client.post("/api/v1/participants", json=ACCEPT, headers={**WRITE, **bearer(token)})
        sid = client.post(
            "/api/v1/sessions", json=SCENARIO, headers={**WRITE, **bearer(owner)}
        ).json()["id"]
        assert client.get(f"/api/v1/sessions/{sid}", headers=bearer(intruder)).status_code == 404
        cross = {"Origin": "https://otro.example.test", "X-Nukyro-Request": "1", **bearer(owner)}
        assert client.post("/api/v1/account/login", json={}, headers=cross).status_code == 403
