"""Caja negra de las evaluaciones de DEMO-BECAS (T-14): tres recorridos por HTTPS hasta terminarlas.

Las puntuaciones esperadas se calcularon a mano (tests/evaluaciones.py). Solo se usa la API.
"""

import os
import ssl

import httpx
import pytest
from evaluaciones import CAUSALES, CLAVE, EVALUACIONES, ORDEN_FINAL
from recorridos import RECORRIDOS

BASE = os.environ["NUKYRO_BASE_URL"]
CA_FILE = os.environ["NUKYRO_CA_FILE"]
WRITE = {"Origin": os.environ["NUKYRO_ORIGIN"], "X-Nukyro-Request": "1"}
ACCEPT = {"age_confirmed": True, "privacy_notice_version": "DEMO-1", "terms_version": "DEMO-1"}
SECRETS = {"is_correct", "correct", "topic", "objective", "assesses", "learning_objective"}


def new_client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE, verify=ssl.create_default_context(cafile=CA_FILE), timeout=15
    )


@pytest.fixture
def person():
    with new_client() as client:
        assert client.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
        yield client


def start(client) -> str:
    body = {"scenario_key": "DEMO-BECAS", "self_reported_first": True}
    r = client.post("/api/v1/sessions", json=body, headers=WRITE)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def url(sid, kind, *rest) -> str:
    return "/".join(["/api/v1/sessions", sid, "assessments", kind, *rest])


def put(client, sid, kind, question, option):
    return client.put(
        url(sid, kind, "answers", question), json={"option_key": option}, headers=WRITE
    )


def submit(client, sid, kind):
    return client.post(url(sid, kind, "submit"), headers=WRITE)


def answer_all(client, sid, outcome, kind):
    for question, option in EVALUACIONES[outcome][kind][0].items():
        assert put(client, sid, kind, question, option).status_code == 200


def keys(value) -> set:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


def play(client, sid, outcome) -> None:
    """Recorre el escenario con los pasos de tests/recorridos.py (el pre-test ya está enviado)."""
    assert (
        client.post(
            f"/api/v1/sessions/{sid}/advance", json={"from_node_key": "intro"}, headers=WRITE
        ).status_code
        == 200
    )
    for node, option, reasons, _, _ in RECORRIDOS[outcome]["steps"]:
        body = {"node_key": node, "option_key": option, "reason_keys": reasons}
        r = client.post(f"/api/v1/sessions/{sid}/decisions", json=body, headers=WRITE)
        assert r.status_code == 200, r.text


def do_pretest(client, sid, outcome) -> None:
    answer_all(client, sid, outcome, "pretest")
    assert submit(client, sid, "pretest").status_code == 200


# --- RF-007 y RF-008 ---


def test_rf007_rf008_el_pretest_se_ve_con_la_sesion_iniciada_sin_correctas_ni_temas(person):
    sid = start(person)
    r = person.get(url(sid, "pretest"))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 6 and data["submitted"] is False and data["score"] is None
    assert [q["key"] for q in data["questions"]] == [f"pre{i}" for i in range(1, 7)]
    assert all(len(q["options"]) == 3 for q in data["questions"])
    assert not keys(data) & SECRETS
    assert "datos personales" not in r.text  # el tema no sale


def test_rf007_una_sesion_ajena_es_404(person):
    sid = start(person)
    with new_client() as other:
        other.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
        assert other.get(url(sid, "pretest")).status_code == 404
        assert put(other, sid, "pretest", "pre1", "b").status_code == 404
        assert submit(other, sid, "pretest").status_code == 404


def test_rf011_incompleto_es_409_y_no_se_sale_del_primer_nodo_sin_enviarlo(person):
    sid = start(person)
    assert put(person, sid, "pretest", "pre1", "b").status_code == 200
    assert submit(person, sid, "pretest").status_code == 409
    adv = person.post(
        f"/api/v1/sessions/{sid}/advance", json={"from_node_key": "intro"}, headers=WRITE
    )
    assert adv.status_code == 409
    assert person.get(f"/api/v1/sessions/{sid}").json()["state"] == "started"


# --- RF-050: nada final antes del desenlace ---


def test_rf050_antes_del_desenlace_el_posttest_la_transferencia_y_la_causal_son_409(person):
    sid = start(person)
    do_pretest(person, sid, "OUT_SOLID")
    for kind in ORDEN_FINAL:
        assert person.get(url(sid, kind)).status_code == 409
        assert submit(person, sid, kind).status_code == 409


# --- Los tres recorridos hasta terminar las evaluaciones ---


@pytest.mark.parametrize("outcome", RECORRIDOS)
def test_recorrido_completo_con_puntuaciones_calculadas_a_mano(person, outcome):
    sid = start(person)
    do_pretest(person, sid, outcome)
    assert person.get(url(sid, "pretest")).json()["score"] == EVALUACIONES[outcome]["pretest"][1]
    assert person.get(f"/api/v1/sessions/{sid}").json()["state"] == "in_scenario"
    play(person, sid, outcome)
    assert person.get(f"/api/v1/sessions/{sid}").json()["state"] == "outcome_reached"
    scores = {"pretest": EVALUACIONES[outcome]["pretest"][1]}
    for i, kind in enumerate(ORDEN_FINAL):
        for later in ORDEN_FINAL[i + 1 :]:  # fuera de su turno
            assert person.get(url(sid, later)).status_code == 409
        shown = person.get(url(sid, kind))
        assert shown.status_code == 200 and not keys(shown.json()) & SECRETS
        if kind == "causal":  # RF-058: solo las que ocurrieron, y las demás se rechazan (422)
            assert [q["key"] for q in shown.json()["questions"]] == CAUSALES[outcome]
            for other in CLAVE["causal"]:
                if other not in CAUSALES[outcome]:
                    assert put(person, sid, kind, other, "a").status_code == 422
        answer_all(person, sid, outcome, kind)
        done = submit(person, sid, kind)
        assert done.status_code == 200, done.text
        assert done.json()["submitted"] is True and not keys(done.json()) & SECRETS
        assert done.json()["score"] == EVALUACIONES[outcome][kind][1]
        scores[kind] = done.json()["score"]
        assert submit(person, sid, kind).json() == done.json()  # repetir no recalifica
        expected = "completed" if kind == "causal" else "outcome_reached"
        assert person.get(f"/api/v1/sessions/{sid}").json()["state"] == expected
    # RF-049: una puntuación por evaluación; ninguna nota global de la persona
    assert set(scores) == {"pretest", *ORDEN_FINAL}
    final = person.get(f"/api/v1/sessions/{sid}")
    assert not keys(final.json()) & {"total_score", "grade", "overall", "moral_score", "level"}
    phases = [p["phase"] for p in final.json()["phases"]]
    assert phases == ["started", "in_scenario", "outcome_reached", "completed"]


def test_las_respuestas_tras_enviar_no_cambian_y_un_conjunto_enviado_no_se_modifica(person):
    sid = start(person)
    do_pretest(person, sid, "OUT_MIXED")
    before = person.get(url(sid, "pretest")).json()
    assert put(person, sid, "pretest", "pre1", "c").status_code == 409
    assert person.get(url(sid, "pretest")).json() == before
