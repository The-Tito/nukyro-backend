"""Derechos del participante por HTTPS y sus efectos en PostgreSQL (T-20)."""

import pytest

from .conftest import ACCEPT, WRITE, bearer, participant_id, secret_of

DATA = "/api/v1/participants/me/data"
OPPOSITION = "/api/v1/participants/me/statistics-opposition"
SCENARIO = {"scenario_key": "DEMO-BECAS", "self_reported_first": True}


def start(client):
    response = client.post("/api/v1/sessions", json=SCENARIO, headers=WRITE)
    assert response.status_code == 201
    return response.json()["id"]


def test_rf078_descarga_solo_sesiones_propias_con_constancias_y_respuestas(person, new_client):
    own = start(person)
    other = new_client()
    assert other.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
    foreign = start(other)
    pretest = f"/api/v1/sessions/{own}/assessments/pretest"
    question = person.get(pretest).json()["questions"][0]
    option = question["options"][0]["key"]
    response = person.put(
        f"{pretest}/answers/{question['key']}", json={"option_key": option}, headers=WRITE
    )
    assert response.is_success

    download = person.get(DATA)
    assert download.status_code == 200
    assert download.headers["content-disposition"] == 'attachment; filename="nukyro-data.json"'
    assert download.headers["cache-control"] == "no-store"
    data = download.json()
    assert not data["exclude_from_stats"]
    assert {item["document_type"] for item in data["acceptances"]} == {
        "age_18_plus",
        "privacy_notice",
        "terms",
    }
    (session,) = data["sessions"]
    assert session["id"] == own
    assert session["steps"][0]["node_key"] == "intro"
    (assessment,) = session["assessments"]
    assert assessment["kind"] == "pretest"
    (answer,) = assessment["answers"]
    assert (answer["question_key"], answer["option_key"]) == (question["key"], option)
    assert foreign not in download.text
    assert secret_of(person) not in download.text
    assert [row["id"] for row in other.get(DATA).json()["sessions"]] == [foreign]


@pytest.mark.parametrize("opposed", [False, True])
def test_rf078_borrar_invalida_el_secreto_y_archiva_segun_la_oposicion(
    person, superuser, new_client, opposed
):
    sid = start(person)
    participant = participant_id(superuser, person)
    secret = secret_of(person)
    if opposed:
        for _ in range(2):
            assert person.put(OPPOSITION, headers=WRITE).status_code == 204
        assert person.get(DATA).json()["exclude_from_stats"]
    before = superuser.execute("SELECT count(*) FROM nukyro.session_facts").fetchone()[0]

    response = person.delete(DATA, headers=WRITE)
    assert response.status_code == 204
    assert response.content == b""
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert (
        new_client()
        .get(DATA, headers={"Cookie": f"__Host-nukyro_participant={secret}"})
        .status_code
        == 401
    )

    assert superuser.execute(
        "SELECT EXISTS (SELECT 1 FROM nukyro.participants WHERE id = %s), "
        "EXISTS (SELECT 1 FROM nukyro.sessions WHERE id = %s)",
        (participant, sid),
    ).fetchone() == (False, False)
    after = superuser.execute("SELECT count(*) FROM nukyro.session_facts").fetchone()[0]
    assert after == before + (not opposed)


def test_rf079_cuenta_puede_oponerse_sin_cambiar_otro_participante(
    person, new_client, mint, superuser
):
    other = participant_id(superuser, person)
    account_client = new_client()
    token_headers = {**WRITE, **bearer(mint())}
    assert (
        account_client.post("/api/v1/account/login", json={}, headers=token_headers).status_code
        == 200
    )
    assert (
        account_client.post("/api/v1/participants", json=ACCEPT, headers=token_headers).status_code
        == 201
    )

    assert person.get(DATA, headers=token_headers).status_code == 403
    assert person.delete(DATA, headers=token_headers).status_code == 403
    for _ in range(2):
        assert person.put(OPPOSITION, headers=token_headers).status_code == 204

    sid = person.post("/api/v1/sessions", json=SCENARIO, headers=token_headers).json()["id"]
    assert superuser.execute(
        "SELECT p.exclude_from_stats FROM nukyro.participants p "
        "JOIN nukyro.sessions s ON s.participant_id = p.id WHERE s.id = %s",
        (sid,),
    ).fetchone() == (True,)
    assert superuser.execute(
        "SELECT exclude_from_stats FROM nukyro.participants WHERE id = %s", (other,)
    ).fetchone() == (False,)


def test_rf070_borrar_una_sesion_antigua_conserva_la_duracion(person, superuser):
    sid = start(person)
    superuser.execute(
        "UPDATE nukyro.sessions SET started_at = now() - interval '29 days', "
        "last_activity_at = now() - interval '1 day' WHERE id = %s",
        (sid,),
    )
    before = superuser.execute(
        "SELECT count(*) FROM nukyro.session_facts WHERE duration_bucket_min = 40320"
    ).fetchone()[0]

    assert person.delete(DATA, headers=WRITE).status_code == 204

    after = superuser.execute(
        "SELECT count(*) FROM nukyro.session_facts WHERE duration_bucket_min = 40320"
    ).fetchone()[0]
    assert after == before + 1
