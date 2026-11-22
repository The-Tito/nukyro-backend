"""Caja negra de la encuesta (T-16): se ofrece al terminar, se responde una vez y no se vincula."""

import pytest
from evaluaciones import ORDEN_FINAL
from test_assessment import ACCEPT, WRITE, answer_all, do_pretest, new_client, play, start, submit

SCALES = [
    "usefulness",
    "clarity",
    "decision_impact",
    "causal_understanding",
    "summary_usefulness",
    "would_repeat",
]


@pytest.fixture
def person():
    with new_client() as client:
        assert client.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
        yield client


def survey(sid) -> str:
    return f"/api/v1/sessions/{sid}/survey"


def finish(client, sid, outcome="OUT_MIXED"):
    do_pretest(client, sid, outcome)
    play(client, sid, outcome)
    for kind in ORDEN_FINAL:
        answer_all(client, sid, outcome, kind)
        assert submit(client, sid, kind).status_code == 200


def test_rf060_la_encuesta_no_se_ofrece_hasta_terminar_y_enviar_antes_es_409(person):
    sid = start(person)
    assert person.get(survey(sid)).json() == {"available": False}
    assert person.post(survey(sid), json={"usefulness": 4}, headers=WRITE).status_code == 409
    do_pretest(person, sid, "OUT_MIXED")
    play(person, sid, "OUT_MIXED")
    assert person.get(survey(sid)).json() == {"available": False}  # con desenlace, sin terminar


def test_rf060_tras_terminar_se_ofrece_se_responde_una_vez_y_solo_queda_respondida(person):
    sid = start(person)
    finish(person, sid)
    data = person.get(survey(sid)).json()
    assert (
        data["available"] is True
        and data["can_skip"] is True
        and data["notice_url"] == "/api/v1/entry"
    )
    assert [q["key"] for q in data["questions"]] == SCALES
    assert person.post(survey(sid), json={"usefulness": 6}, headers=WRITE).status_code == 422
    done = person.post(survey(sid), json={"usefulness": 5, "would_repeat": 4}, headers=WRITE)
    assert done.status_code == 201 and done.json() == {"submitted": True}
    assert person.get(survey(sid)).json() == {"available": False}
    assert person.post(survey(sid), json={"usefulness": 1}, headers=WRITE).status_code == 409
    assert person.get(f"/api/v1/sessions/{sid}/summary").status_code == 200  # el resumen sigue
    assert (
        "usefulness" not in person.get(f"/api/v1/sessions/{sid}").text
    )  # la sesión no guarda la respuesta


def test_rf060_una_sesion_ajena_es_404(person):
    sid = start(person)
    finish(person, sid)
    with new_client() as other:
        other.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
        assert other.get(survey(sid)).status_code == 404
        assert other.post(survey(sid), json={"usefulness": 3}, headers=WRITE).status_code == 404
