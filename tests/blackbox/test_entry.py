"""Caja negra del recorrido de entrada (T-10): solo HTTPS, sin importar la aplicación.

Cada prueba se llama como el RF que cubre (etapa-2, «Criterios por RF»).
"""

import os
import re
import ssl
import uuid
from datetime import UTC, datetime

import httpx
import pytest

BASE = os.environ["NUKYRO_BASE_URL"]
CA_FILE = os.environ["NUKYRO_CA_FILE"]
ORIGIN = os.environ["NUKYRO_ORIGIN"]
COOKIE = "__Host-nukyro_participant"
WRITE = {"Origin": ORIGIN, "X-Nukyro-Request": "1"}
ACCEPT = {"age_confirmed": True, "privacy_notice_version": "DEMO-1", "terms_version": "DEMO-1"}
SCENARIO = {"scenario_key": "DEMO-BECAS", "self_reported_first": True}
FORBIDDEN_KEYS = {"participant_id", "variables", "rules", "effects", "options", "next_node_id"}


def new_client() -> httpx.Client:
    context = ssl.create_default_context(cafile=CA_FILE)
    return httpx.Client(base_url=BASE, verify=context, timeout=10)


@pytest.fixture
def anon():
    with new_client() as client:
        yield client


@pytest.fixture
def person():
    """Participante con las tres aceptaciones y su cookie en el cliente."""
    with new_client() as client:
        response = client.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
        assert response.status_code == 201
        yield client


def keys(value) -> set[str]:
    """Todas las claves de un JSON anidado."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


def start(client, body=SCENARIO):
    return client.post("/api/v1/sessions", json=body, headers=WRITE)


# --- RF-068: aviso y documentos sin cookie ---


def test_rf068_entry_publica_responsable_categorias_finalidades_plazo_y_contacto(anon):
    response = anon.get("/api/v1/entry")
    assert response.status_code == 200
    data = response.json()
    notice = data["privacy_notice"]
    for field in ("controller", "categories", "purposes", "retention", "contact"):
        assert notice[field]
    assert notice["contact"] == "privacidad@example.test"
    assert "DEMOSTRACIÓN, sin validez legal" in notice["marker"]
    assert {d["type"] for d in data["documents"]} == {"privacy_notice", "terms"}
    for doc in data["documents"]:
        assert doc["version"] == "DEMO-1"
        assert "DEMOSTRACIÓN, sin validez legal" in doc["text"]
    assert "DEMO-BECAS" in [s["key"] for s in data["scenarios"]]
    assert response.headers["cache-control"] == "no-store"


def test_rf068_consultar_no_emite_cookie(anon):
    response = anon.get("/api/v1/entry")
    assert "set-cookie" not in response.headers


# --- RF-073 y RF-062: aceptación, participante y cookie ---


def test_rf073_las_tres_aceptaciones_crean_participante_201(anon):
    response = anon.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
    assert response.status_code == 201
    assert not keys(response.json()) & FORBIDDEN_KEYS


@pytest.mark.parametrize("missing", list(ACCEPT))
def test_rf073_si_falta_una_aceptacion_es_422(anon, missing):
    body = {k: v for k, v in ACCEPT.items() if k != missing}
    response = anon.post("/api/v1/participants", json=body, headers=WRITE)
    assert response.status_code == 422
    assert "set-cookie" not in response.headers


def test_rf073_confirmacion_de_edad_falsa_es_422(anon):
    response = anon.post(
        "/api/v1/participants", json={**ACCEPT, "age_confirmed": False}, headers=WRITE
    )
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["privacy_notice_version", "terms_version"])
def test_rf073_version_que_no_es_la_vigente_es_422(anon, field):
    response = anon.post("/api/v1/participants", json={**ACCEPT, field: "DEMO-0"}, headers=WRITE)
    assert response.status_code == 422
    assert "DEMO-0" not in response.text


def test_rf073_tipos_estrictos_y_campos_desconocidos_son_422(anon):
    for body in (
        {**ACCEPT, "age_confirmed": "true"},
        {**ACCEPT, "terms_version": 1},
        {**ACCEPT, "participant_id": str(uuid.uuid4())},
    ):
        assert anon.post("/api/v1/participants", json=body, headers=WRITE).status_code == 422


def test_rf073_con_cookie_valida_no_se_crea_otro_participante(person):
    response = person.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
    assert response.status_code == 200


def test_rf062_la_cookie_es_host_secure_httponly_samesite_path(anon):
    response = anon.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    low = cookie.lower()
    for attr in ("secure", "httponly", "samesite=lax", "path=/", "max-age=2592000"):
        assert attr in low
    assert "domain" not in low
    secret = re.match(rf"{COOKIE}=([^;]+)", cookie).group(1)
    assert len(secret) >= 43  # 256 bits en base64url
    assert secret not in response.text


def test_rf062_cookie_alterada_es_401(person):
    person.cookies.clear()
    person.cookies.set(COOKIE, "alterada-" + "x" * 40, domain="proxy")
    assert person.get("/api/v1/sessions").status_code == 401
    assert start(person).status_code == 401


def test_rf062_la_cookie_se_renueva_al_usarse(person):
    response = person.get("/api/v1/sessions")
    assert response.status_code == 200
    assert "max-age=2592000" in response.headers["set-cookie"].lower()


def test_rf062_sesion_ajena_es_404_igual_que_inexistente(person):
    mine = start(person).json()["id"]
    with new_client() as other:
        other.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
        foreign = other.get(f"/api/v1/sessions/{mine}")
        missing = other.get(f"/api/v1/sessions/{uuid.uuid4()}")
        malformed = other.get("/api/v1/sessions/no-es-uuid")
        assert other.get("/api/v1/sessions").json()["sessions"] == []
    assert foreign.status_code == missing.status_code == malformed.status_code == 404
    assert foreign.json() == missing.json() == malformed.json()
    assert person.get(f"/api/v1/sessions/{mine}").status_code == 200


def test_rf062_el_secreto_no_sale_en_ningun_cuerpo(person):
    secret = person.cookies.get(COOKIE)
    assert secret
    for response in (
        person.get("/api/v1/entry"),
        person.post("/api/v1/participants", json=ACCEPT, headers=WRITE),
        start(person),
        person.get("/api/v1/sessions"),
        person.post("/api/v1/sessions", json={"scenario_key": 1}, headers=WRITE),
    ):
        assert secret not in response.text


# --- RF-001 a RF-004: iniciar sesión ---


def test_rf001_con_participante_valido_se_crea_la_sesion_201(person):
    response = start(person)
    assert response.status_code == 201
    data = response.json()
    assert data["current_node"]["type"] == "intro"
    assert data["state"] == "started"
    assert data["is_first_session"] is True
    assert not keys(data) & FORBIDDEN_KEYS
    assert set(data["current_node"]) == {"key", "type", "title", "body"}


def test_rf001_sin_cookie_es_401(anon):
    assert start(anon).status_code == 401


def test_rf001_escenario_inexistente_es_404(person):
    assert start(person, {**SCENARIO, "scenario_key": "NO-EXISTE"}).status_code == 404
    assert person.get("/api/v1/sessions").json()["sessions"] == []


def test_rf001_segunda_sesion_no_es_la_primera(person):
    assert start(person).json()["is_first_session"] is True
    assert start(person).json()["is_first_session"] is False
    assert (
        start(person, {**SCENARIO, "self_reported_first": False}).json()["is_first_session"]
        is False
    )


def test_rf002_dos_sesiones_reciben_uuid_distintos(person):
    first, second = start(person).json()["id"], start(person).json()["id"]
    assert uuid.UUID(first) != uuid.UUID(second)
    assert {s["id"] for s in person.get("/api/v1/sessions").json()["sessions"]} == {first, second}


def test_rf002_un_id_enviado_se_rechaza_422(person):
    response = start(person, {**SCENARIO, "id": str(uuid.uuid4())})
    assert response.status_code == 422
    assert person.get("/api/v1/sessions").json()["sessions"] == []


def test_rf003_la_sesion_devuelve_escenario_y_version_publicada(person):
    data = start(person).json()
    assert data["scenario"]["key"] == "DEMO-BECAS"
    assert data["scenario"]["version_number"] == 1
    assert "DEMOSTRACIÓN" in data["scenario"]["title"]
    assert data["scenario"]["introduction"].startswith("DEMOSTRACIÓN")


def test_rf003_un_version_id_enviado_se_rechaza_422(person):
    assert start(person, {**SCENARIO, "version_id": str(uuid.uuid4())}).status_code == 422


def test_rf004_started_at_lo_pone_el_servidor_en_utc(person):
    before = datetime.now(UTC)
    data = start(person).json()
    started = datetime.fromisoformat(data["started_at"])
    assert started.utcoffset().total_seconds() == 0
    assert abs((started - before).total_seconds()) < 30


def test_rf004_un_started_at_enviado_se_rechaza_422(person):
    assert start(person, {**SCENARIO, "started_at": "2020-01-01T00:00:00Z"}).status_code == 422


@pytest.mark.parametrize(
    "body", [{"scenario_key": "DEMO-BECAS"}, {**SCENARIO, "self_reported_first": "si"}, {}]
)
def test_rf001_cuerpo_invalido_es_422_sin_reflejar_la_entrada(person, body):
    response = person.post(
        "/api/v1/sessions", json={**body, "x": "valor-secreto-789"}, headers=WRITE
    )
    assert response.status_code == 422
    assert "valor-secreto-789" not in response.text


# --- CSRF en cada escritura ---


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": ORIGIN},
        {"X-Nukyro-Request": "1"},
        {"Origin": "https://otro.example.test", "X-Nukyro-Request": "1"},
        {"Origin": ORIGIN + "/", "X-Nukyro-Request": "1"},
        {"Origin": ORIGIN, "X-Nukyro-Request": "0"},
    ],
)
def test_csrf_toda_escritura_sin_origin_y_cabecera_exactos_es_403(person, headers):
    for path, body in (("/api/v1/participants", ACCEPT), ("/api/v1/sessions", SCENARIO)):
        response = person.post(path, json=body, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
    assert person.put("/api/v1/sessions", json={}, headers=headers).status_code == 403
    assert person.get("/api/v1/sessions").json()["sessions"] == []


def test_la_api_no_se_cachea(person):
    for response in (person.get("/api/v1/sessions"), person.get("/api/v1/health"), start(person)):
        assert response.headers["cache-control"] == "no-store"
    assert person.get("/api/v1/no-existe").headers["cache-control"] == "no-store"
