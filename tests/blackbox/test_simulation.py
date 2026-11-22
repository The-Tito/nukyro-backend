"""Caja negra de la simulación (T-07): solo HTTPS, sin importar la aplicación.

Cada prueba se llama como el RF que cubre (etapa-3, «Criterios por RF»). Los escenarios T07-NEGRO y
T07-NEGRO-PRETEST los siembra la preparación (tests/blackbox/seed-simulation.sql): en el primero el
pre-test nace completado porque E4 lo califica; en el segundo queda pendiente.
Recorrido: intro, INFO, D1 (A: p-2, B: p+1; razones R1 correcta y R2 incorrecta), D2 (C: p-2,
D: p+1), EVR (evento en la ruta) y BUENO. A y luego C dan el evento EV y el final MALO.
"""

import os
import ssl

import httpx
import pytest

BASE = os.environ["NUKYRO_BASE_URL"]
CA_FILE = os.environ["NUKYRO_CA_FILE"]
ORIGIN = os.environ["NUKYRO_ORIGIN"]
COOKIE = "__Host-nukyro_participant"
WRITE = {"Origin": ORIGIN, "X-Nukyro-Request": "1"}
ACCEPT = {"age_confirmed": True, "privacy_notice_version": "DEMO-1", "terms_version": "DEMO-1"}
READY = "T07-NEGRO"
PENDING = "T07-NEGRO-PRETEST"
INTERNAL = {
    "variables",
    "value",
    "effects",
    "rules",
    "condition",
    "priority",
    "relation_type",
    "explanation",
    "is_correct",
    "correct",
    "next_node_id",
    "next_node_key",
    "default_next_node_id",
    "participant_id",
}


def new_client() -> httpx.Client:
    context = ssl.create_default_context(cafile=CA_FILE)
    return httpx.Client(base_url=BASE, verify=context, timeout=15)


@pytest.fixture
def person():
    with new_client() as client:
        assert client.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
        yield client


def keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


def start(client, scenario=READY) -> str:
    r = client.post(
        "/api/v1/sessions",
        json={"scenario_key": scenario, "self_reported_first": True},
        headers=WRITE,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def get(client, sid):
    return client.get(f"/api/v1/sessions/{sid}")


def node_of(client, sid) -> str:
    return get(client, sid).json()["current_node"]["key"]


def advance(client, sid, node, body=None):
    return client.post(
        f"/api/v1/sessions/{sid}/advance", json=body or {"from_node_key": node}, headers=WRITE
    )


def decide(client, sid, node, option, reasons=(), extra=None):
    body = {"node_key": node, "option_key": option, "reason_keys": list(reasons), **(extra or {})}
    return client.post(f"/api/v1/sessions/{sid}/decisions", json=body, headers=WRITE)


def at_d1(client) -> str:
    sid = start(client)
    assert advance(client, sid, "intro").status_code == 200
    assert advance(client, sid, "INFO").status_code == 200
    assert node_of(client, sid) == "D1"
    return sid


def at_d2(client, option="A") -> str:
    sid = at_d1(client)
    assert decide(client, sid, "D1", option, ["R1"]).status_code == 200
    assert node_of(client, sid) == "D2"
    return sid


# --- RF-006: retomar ---


def test_rf006_otra_peticion_con_la_cookie_retoma_el_ultimo_nodo_confirmado(person):
    sid = at_d2(person)
    with new_client() as another_tab:
        another_tab.headers["Cookie"] = f"{COOKIE}={person.cookies.get(COOKIE)}"
        resumed = get(another_tab, sid)
    assert resumed.status_code == 200
    assert resumed.json()["current_node"]["key"] == "D2"
    assert [o["key"] for o in resumed.json()["options"]] == ["C", "D"]


def test_rf006_otra_cookie_es_404_y_una_decision_revertida_no_avanza(person):
    sid = at_d1(person)
    with new_client() as other:
        other.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
        assert get(other, sid).status_code == 404
        assert decide(other, sid, "D1", "A", ["R1"]).status_code == 404
    assert node_of(person, sid) == "D1"
    assert (
        decide(person, sid, "D1", "A", ["R9"]).status_code == 422
    )  # razón desconocida: se revierte
    assert node_of(person, sid) == "D1"
    assert get(person, sid).json()["events"] == []


# --- RF-013: introducción ---


def test_rf013_la_intro_muestra_titulo_y_contexto_del_escenario(person):
    data = get(person, start(person)).json()
    assert data["scenario"]["title"] == f"{READY} DEMOSTRACIÓN"
    assert data["current_node"] == {
        "key": "intro",
        "type": "intro",
        "title": "Título intro",
        "body": "Texto narrativo intro",
    }


def test_rf013_la_intro_no_expone_reglas_ni_variables(person):
    sid = start(person)
    for response in (get(person, sid), person.get("/api/v1/sessions")):
        assert not keys(response.json()) & INTERNAL
        assert "RULE-" not in response.text and "Explicación interna" not in response.text
    assert get(person, sid).json()["options"] == []


# --- RF-014 y RF-015: los cuatro tipos de nodo por la ruta del motor ---


def test_rf014_rf015_la_ruta_recorre_narrativo_decision_evento_y_desenlace(person):
    sid = at_d1(person)
    types = {"INFO": "info", "D1": "decision", "D2": "decision", "EVR": "event", "BUENO": "outcome"}
    seen = ["INFO"]  # at_d1 ya pasó por el nodo narrativo
    assert decide(person, sid, "D1", "B", ["R1"]).status_code == 200
    assert decide(person, sid, "D2", "D").status_code == 200
    assert node_of(person, sid) == "EVR"
    assert advance(person, sid, "EVR").status_code == 200
    data = get(person, sid).json()
    assert data["current_node"]["key"] == "BUENO"
    seen += ["D1", "D2", "EVR", "BUENO"]
    assert {types[k] for k in seen} == {"info", "decision", "event", "outcome"}
    assert data["current_node"]["type"] == "outcome" and data["state"] == "outcome_reached"


def test_rf014_rf015_un_destino_enviado_por_el_cliente_es_422_y_no_mueve_nada(person):
    sid = at_d1(person)
    for body in (
        {"node_key": "D1", "option_key": "A", "reason_keys": ["R1"], "next_node_key": "BUENO"},
        {"node_key": "D1", "option_key": "A", "reason_keys": ["R1"], "next_node_id": "x"},
    ):
        assert (
            person.post(f"/api/v1/sessions/{sid}/decisions", json=body, headers=WRITE).status_code
            == 422
        )
    assert (
        advance(person, sid, "D1", {"from_node_key": "D1", "to_node_key": "BUENO"}).status_code
        == 422
    )
    assert node_of(person, sid) == "D1"


# --- RF-016: avanzar ---


def test_rf016_avanzar_mueve_un_nodo_y_repetir_no_mueve_otro(person):
    sid = start(person)
    first = advance(person, sid, "intro")
    assert first.status_code == 200 and first.json()["current_node"]["key"] == "INFO"
    again = advance(person, sid, "intro")  # reintento de la misma petición
    assert again.status_code == 200 and again.json()["current_node"]["key"] == "INFO"
    assert node_of(person, sid) == "INFO"


def test_rf016_con_el_pretest_pendiente_avanzar_es_409(person):
    sid = start(person, PENDING)
    assert get(person, sid).json()["state"] == "started"
    assert advance(person, sid, "intro").status_code == 409
    assert node_of(person, sid) == "intro"


# --- RF-017 y RF-024: decidir con razones ---


def test_rf017_rf024_con_decision_y_razones_exigidas_se_continua(person):
    sid = at_d1(person)
    r = decide(person, sid, "D1", "B", ["R1", "R2"])
    assert r.status_code == 200
    body = r.json()
    assert body["replayed"] is False
    assert body["confirmed"] == {"node_key": "D1", "option_key": "B", "reason_keys": ["R1", "R2"]}
    assert body["session"]["current_node"]["key"] == "D2"


def test_rf017_rf024_sin_decision_es_409_y_sin_razones_exigidas_es_422_sin_cambios(person):
    sid = at_d1(person)
    assert advance(person, sid, "D1").status_code == 409  # decisión pendiente
    assert decide(person, sid, "D1", "A").status_code == 422  # se exigen razones
    assert decide(person, sid, "D1", "A", ["R1", "R1"]).status_code == 422
    after = get(person, sid).json()
    assert after["current_node"]["key"] == "D1" and after["events"] == []
    assert decide(person, sid, "D1", "A", ["R1"]).status_code == 200  # nada quedó a medias


# --- RF-018 y RF-038: desenlace ---


def test_rf018_rf038_el_desenlace_se_muestra_y_marca_el_fin(person):
    sid = at_d2(person, "A")
    last = decide(person, sid, "D2", "C")
    assert last.status_code == 200
    data = last.json()["session"]
    assert data["current_node"] == {
        "key": "MALO",
        "type": "outcome",
        "title": "Título MALO",
        "body": "Texto narrativo MALO",
    }
    assert data["state"] == "outcome_reached"
    assert get(person, sid).json()["state"] == "outcome_reached"


def test_rf018_rf038_avanzar_desde_el_desenlace_es_409(person):
    sid = at_d2(person, "A")
    assert decide(person, sid, "D2", "C").status_code == 200
    assert advance(person, sid, "MALO").status_code == 409
    data = get(person, sid).json()
    assert data["current_node"]["key"] == "MALO" and data["state"] == "outcome_reached"


# --- RF-019: alternativas del nodo actual ---


def test_rf019_se_listan_las_alternativas_y_razones_del_nodo_actual(person):
    sid = at_d1(person)
    data = get(person, sid).json()
    assert data["options"] == [
        {"key": "A", "label": "Alternativa A"},
        {"key": "B", "label": "Alternativa B"},
    ]
    assert data["reasons"] == [
        {"key": "R1", "label": "Razón R1"},
        {"key": "R2", "label": "Razón R2"},
    ]
    assert decide(person, sid, "D1", "A", ["R1"]).status_code == 200
    assert [o["key"] for o in get(person, sid).json()["options"]] == ["C", "D"]


def test_rf019_las_alternativas_no_llevan_efectos_destinos_ni_razones_correctas(person):
    sid = at_d1(person)
    data = get(person, sid).json()
    assert all(set(item) == {"key", "label"} for item in data["options"] + data["reasons"])
    assert not keys(data) & INTERNAL
    assert not keys(data) & {"next_node_id", "effects"}


# --- RF-035: solo texto narrativo ---


def test_rf035_los_eventos_son_solo_texto_narrativo_del_contenido(person):
    sid = at_d2(person, "A")
    data = decide(person, sid, "D2", "C").json()["session"]
    assert data["events"] == [{"title": "Título EV", "body": "Texto narrativo EV"}]
    assert get(person, sid).json()["events"] == data["events"]


def test_rf035_ninguna_respuesta_lleva_valores_de_variables(person):
    sid = start(person)
    responses = [get(person, sid), advance(person, sid, "intro"), advance(person, sid, "INFO")]
    responses += [decide(person, sid, "D1", "A", ["R1"]), decide(person, sid, "D2", "C")]
    responses += [get(person, sid), person.get("/api/v1/sessions")]
    for r in responses:
        assert r.status_code == 200
        assert not keys(r.json()) & INTERNAL
        assert '"p"' not in r.text and "RULE-" not in r.text
