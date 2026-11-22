# ruff: noqa: E501
"""Encuesta no vinculada contra la API y la base reales (T-16, RF-060, D-29, ADR-007)."""

import pytest

from .conftest import WRITE, participant_id
from .test_assessment import build, start

SCALES = (
    "usefulness",
    "clarity",
    "decision_impact",
    "causal_understanding",
    "summary_usefulness",
    "would_repeat",
)


@pytest.fixture(scope="module")
def key(superuser):
    return build(superuser)


def finished(person, superuser, key) -> str:
    """Sesión iniciada y terminada (el hito se fija con el superusuario: el recorrido ya se prueba)."""
    sid = start(person, key)
    superuser.execute(
        "UPDATE nukyro.sessions SET pretest_completed_at = now(), outcome_reached_at = now(), "
        "outcome_node_id = current_node_id, completed_at = now() WHERE id = %s",
        (sid,),
    )
    return sid


def survey(sid) -> str:
    return f"/api/v1/sessions/{sid}/survey"


def count(superuser) -> int:
    return superuser.execute("SELECT count(*) FROM nukyro.survey_responses").fetchone()[0]


def test_rf060_al_terminar_se_ofrece_con_nota_enlace_omitir_y_las_seis_escalas(
    person, superuser, key
):
    sid = finished(person, superuser, key)
    data = person.get(survey(sid)).json()
    assert data["available"] is True and data["can_skip"] is True
    assert data["notice_url"] == "/api/v1/entry" and "voluntaria" in data["note"]
    assert tuple(q["key"] for q in data["questions"]) == SCALES
    assert [q["key"] for q in data["questions"] if q["required"]] == ["usefulness"]


def test_rf060_sin_terminar_no_se_ofrece_y_enviar_es_409(person, superuser, key):
    sid = start(person, key)
    assert person.get(survey(sid)).json() == {"available": False}
    before = count(superuser)
    assert person.post(survey(sid), json={"usefulness": 4}, headers=WRITE).status_code == 409
    assert count(superuser) == before


def test_rf060_envia_una_vez_marca_solo_respondida_y_no_renueva_la_actividad(
    person, superuser, key
):
    sid = finished(person, superuser, key)
    last = superuser.execute(
        "SELECT last_activity_at FROM nukyro.sessions WHERE id = %s", (sid,)
    ).fetchone()[0]
    before = count(superuser)
    r = person.post(survey(sid), json={"usefulness": 5, "clarity": 3}, headers=WRITE)
    assert r.status_code == 201 and r.json() == {"submitted": True}
    answered, after = superuser.execute(
        "SELECT survey_answered, last_activity_at FROM nukyro.sessions WHERE id = %s", (sid,)
    ).fetchone()
    assert answered is True and after == last  # la sesión no renueva su actividad con la encuesta
    assert count(superuser) == before + 1
    assert person.get(survey(sid)).json() == {"available": False}
    assert person.post(survey(sid), json={"usefulness": 1}, headers=WRITE).status_code == 409
    assert count(superuser) == before + 1  # la segunda vez no inserta


def test_rf060_escala_fuera_de_rango_o_sin_obligatoria_es_422_y_no_deja_nada(
    person, superuser, key
):
    sid = finished(person, superuser, key)
    before = count(superuser)
    for body in (
        {"usefulness": 0},
        {"usefulness": 6},
        {"clarity": 3},
        {"usefulness": 3, "otra": 1},
    ):
        assert person.post(survey(sid), json=body, headers=WRITE).status_code == 422
    assert count(superuser) == before
    assert person.get(survey(sid)).json()["available"] is True


def test_d29_el_participante_opuesto_no_la_ve_y_enviar_es_403(person, superuser, key):
    sid = finished(person, superuser, key)
    superuser.execute(
        "UPDATE nukyro.participants SET exclude_from_stats = true WHERE id = %s",
        (participant_id(superuser, person),),
    )
    before = count(superuser)
    assert person.get(survey(sid)).json() == {"available": False}
    assert person.post(survey(sid), json={"usefulness": 4}, headers=WRITE).status_code == 403
    assert count(superuser) == before


def test_rf060_la_sesion_ajena_es_404_y_sin_csrf_es_403(person, new_client, superuser, key):
    sid = finished(person, superuser, key)
    other = new_client()
    other.post(
        "/api/v1/participants",
        json={"age_confirmed": True, "privacy_notice_version": "DEMO-1", "terms_version": "DEMO-1"},
        headers=WRITE,
    )
    assert other.get(survey(sid)).status_code == 404
    assert other.post(survey(sid), json={"usefulness": 4}, headers=WRITE).status_code == 404
    assert person.post(survey(sid), json={"usefulness": 4}).status_code == 403


def test_rf060_sin_vinculo_las_filas_comparten_xmin_y_no_hay_id_ni_fecha_de_la_sesion(
    person, new_client, superuser, key
):
    for client in (person, new_client()):
        if client is not person:
            client.post(
                "/api/v1/participants",
                json={
                    "age_confirmed": True,
                    "privacy_notice_version": "DEMO-1",
                    "terms_version": "DEMO-1",
                },
                headers=WRITE,
            )
        sid = finished(client, superuser, key)
        assert client.post(survey(sid), json={"usefulness": 4}, headers=WRITE).status_code == 201
    assert (
        superuser.execute(
            "SELECT count(DISTINCT xmin::text) FROM nukyro.survey_responses"
        ).fetchone()[0]
        == 1
    )
    columns = {
        r[0]
        for r in superuser.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'nukyro' AND table_name = 'survey_responses'"
        )
    }
    assert not columns & {"session_id", "participant_id", "created_at", "submitted_at"}
