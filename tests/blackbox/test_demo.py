"""Caja negra de DEMO-BECAS (T-13): los tres recorridos calculados a mano, solo por HTTPS.

Con self_reported_first = false la sesión nace con el pre-test completado
(tests/blackbox/seed-simulation.sql); con true queda pendiente (D-28).
"""

import os
import ssl

import httpx
import pytest
from recorridos import RECORRIDOS

BASE = os.environ["NUKYRO_BASE_URL"]
CA_FILE = os.environ["NUKYRO_CA_FILE"]
WRITE = {"Origin": os.environ["NUKYRO_ORIGIN"], "X-Nukyro-Request": "1"}
ACCEPT = {"age_confirmed": True, "privacy_notice_version": "DEMO-1", "terms_version": "DEMO-1"}


@pytest.fixture
def person():
    context = ssl.create_default_context(cafile=CA_FILE)
    with httpx.Client(base_url=BASE, verify=context, timeout=15) as client:
        assert client.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
        yield client


def start(client, first) -> str:
    body = {"scenario_key": "DEMO-BECAS", "self_reported_first": first}
    r = client.post("/api/v1/sessions", json=body, headers=WRITE)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def advance(client, sid, node):
    return client.post(
        f"/api/v1/sessions/{sid}/advance", json={"from_node_key": node}, headers=WRITE
    )


def test_con_el_pretest_pendiente_no_se_sale_de_la_intro(person):
    sid = start(person, True)
    assert advance(person, sid, "intro").status_code == 409
    assert person.get(f"/api/v1/sessions/{sid}").json()["current_node"]["key"] == "intro"


def test_la_sesion_muestra_la_introduccion_demostracion_de_su_version(person):
    sid = start(person, True)
    data = person.get(f"/api/v1/sessions/{sid}").json()
    assert data["scenario"]["version_number"] == 1
    assert data["scenario"]["introduction"].startswith("DEMOSTRACIÓN. Escenario ficticio")
    assert "no tiene validez legal" in data["scenario"]["introduction"]
    assert person.get(f"/api/v1/sessions/{sid}").json()["scenario"] == data["scenario"]
    assert person.get("/api/v1/sessions").json()["sessions"][0]["scenario"] == data["scenario"]


@pytest.mark.parametrize("outcome", RECORRIDOS)
def test_recorrido_por_https_llega_al_desenlace_y_muestra_los_eventos(person, outcome):
    expected = RECORRIDOS[outcome]
    sid = start(person, False)
    assert advance(person, sid, "intro").status_code == 200
    for node, option, reasons, _, _ in expected["steps"]:
        current = person.get(f"/api/v1/sessions/{sid}").json()
        assert current["current_node"]["key"] == node
        assert option in [o["key"] for o in current["options"]]
        body = {"node_key": node, "option_key": option, "reason_keys": reasons}
        response = person.post(f"/api/v1/sessions/{sid}/decisions", json=body, headers=WRITE)
        assert response.status_code == 200, response.text
    data = person.get(f"/api/v1/sessions/{sid}").json()
    assert data["current_node"]["key"] == outcome and data["state"] == "outcome_reached"
    assert [e["title"] for e in data["events"]] == expected["event_titles"]
    assert "privacy" not in person.get(f"/api/v1/sessions/{sid}").text
