"""Recorrido de entrada contra la API real y la base real (T-10).

Lo que exige mirar la base va aquí; la caja negra pura está en tests/blackbox.
"""

import hashlib
import threading
import uuid

import psycopg
import pytest

from .conftest import ACCEPT, WRITE, compose, connect, participant_id, secret_of

SCENARIO = {"scenario_key": "DEMO-BECAS", "self_reported_first": True}
CONTENT = (
    "scenarios",
    "scenario_versions",
    "nodes",
    "state_variables",
    "decision_points",
    "options",
)


def counts(db) -> tuple:
    return tuple(
        db.execute(f"SELECT count(*) FROM nukyro.{t}").fetchone()[0]
        for t in ("participants", "document_acceptances", "sessions", "session_steps")
    )


def content_digest(db) -> str:
    parts = [
        f"(SELECT coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '') FROM nukyro.{t} t)"
        for t in CONTENT
    ]
    return db.execute("SELECT " + " || ".join(parts)).fetchone()[0]


def make_scenario(db, status: str) -> str:
    """Escenario mínimo propio de la prueba, en el estado pedido (draft, published o retired)."""
    key = f"T10-{status}-{uuid.uuid4().hex[:8]}"
    sid = db.execute(
        "INSERT INTO nukyro.scenarios (key, title) VALUES (%s, %s) RETURNING id", (key, key)
    ).fetchone()[0]
    vid = db.execute(
        "INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title, introduction) "
        "VALUES (%s, 1, %s, %s) RETURNING id",
        (sid, f"{key} DEMOSTRACIÓN", f"DEMOSTRACIÓN: introducción de la versión 1 de {key}"),
    ).fetchone()[0]
    db.execute(
        "INSERT INTO nukyro.nodes (version_id, key, node_type, title, body) "
        "VALUES (%s, 'intro', 'intro', 'Inicio', 'Texto de demostración')",
        (vid,),
    )
    if status in ("published", "retired"):
        db.execute(
            "UPDATE nukyro.scenario_versions SET status='published', published_at=now() "
            "WHERE id=%s",
            (vid,),
        )
    if status == "retired":
        db.execute(
            "UPDATE nukyro.scenario_versions SET status='retired', retired_at=now() WHERE id=%s",
            (vid,),
        )
    return key


# --- RF-062 y RF-073: lo que queda en la base ---


def test_rf062_en_la_base_solo_hay_el_sha256_del_secreto(person, superuser):
    secret = secret_of(person)
    digest = hashlib.sha256(secret.encode()).digest()
    rows = superuser.execute(
        "SELECT secret_hash, p::text FROM nukyro.participants p WHERE secret_hash = %s", (digest,)
    ).fetchall()
    assert len(rows) == 1
    assert secret not in rows[0][1]
    assert superuser.execute(
        "SELECT count(*) FROM nukyro.participants WHERE secret_hash = %s", (secret.encode(),)
    ).fetchone() == (0,)


def test_rf073_tres_aceptaciones_con_version_y_fecha_en_una_transaccion(person, superuser):
    pid = participant_id(superuser, person)
    rows = superuser.execute(
        "SELECT document_type, document_version, accepted_at, "
        "accepted_at - (SELECT created_at FROM nukyro.participants WHERE id = %s) "
        "FROM nukyro.document_acceptances WHERE participant_id = %s ORDER BY document_type",
        (pid, pid),
    ).fetchall()
    assert [(r[0], r[1]) for r in rows] == [
        ("age_18_plus", None),
        ("privacy_notice", "DEMO-1"),
        ("terms", "DEMO-1"),
    ]
    assert all(r[2] is not None and abs(r[3].total_seconds()) < 5 for r in rows)


def test_rf073_cada_422_deja_cero_filas(new_client, superuser):
    client = new_client()
    before = counts(superuser)
    bad = [
        {k: v for k, v in ACCEPT.items() if k != "terms_version"},
        {**ACCEPT, "age_confirmed": False},
        {**ACCEPT, "privacy_notice_version": "DEMO-0"},
        {**ACCEPT, "extra": 1},
    ]
    for body in bad:
        assert client.post("/api/v1/participants", json=body, headers=WRITE).status_code == 422
    assert counts(superuser) == before


def test_rf001_los_rechazos_de_sesion_no_escriben(person, superuser):
    before = counts(superuser)
    for body in (
        {**SCENARIO, "id": str(uuid.uuid4())},
        {**SCENARIO, "started_at": "2020-01-01T00:00:00Z"},
        {**SCENARIO, "version_id": str(uuid.uuid4())},
        {**SCENARIO, "scenario_key": "NO-EXISTE"},
    ):
        assert person.post("/api/v1/sessions", json=body, headers=WRITE).status_code in (404, 422)
    assert counts(superuser) == before


def test_rf073_al_cambiar_la_version_se_acepta_de_nuevo_con_la_misma_cookie(person, superuser):
    pid = participant_id(superuser, person)
    # Como si hubiera aceptado una versión anterior de los documentos
    superuser.execute(
        "UPDATE nukyro.document_acceptances SET document_version = 'DEMO-0' "
        "WHERE participant_id = %s AND document_type <> 'age_18_plus'",
        (pid,),
    )
    assert person.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).status_code == 422
    again = person.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
    assert (again.status_code, again.json()["status"]) == (200, "existing")
    assert participant_id(superuser, person) == pid
    assert person.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).status_code == 201
    assert superuser.execute(
        "SELECT count(*) FROM nukyro.document_acceptances WHERE participant_id = %s", (pid,)
    ).fetchone() == (5,)


def test_rf001_sin_cookie_no_se_escribe(new_client, superuser):
    client = new_client()
    before = counts(superuser)
    assert client.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).status_code == 401
    assert counts(superuser) == before


def test_rf073_sin_las_tres_aceptaciones_vigentes_no_hay_sesion(person, superuser):
    pid = participant_id(superuser, person)
    before = counts(superuser)
    superuser.execute(
        "DELETE FROM nukyro.document_acceptances WHERE participant_id=%s AND document_type='terms'",
        (pid,),
    )
    assert person.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).status_code == 422
    superuser.execute(
        "INSERT INTO nukyro.document_acceptances (participant_id, document_type, document_version) "
        "VALUES (%s, 'terms', 'DEMO-0')",
        (pid,),
    )
    assert person.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).status_code == 422
    assert counts(superuser)[2:] == before[2:]
    superuser.execute(
        "UPDATE nukyro.document_acceptances SET document_version='DEMO-1' "
        "WHERE participant_id=%s AND document_type='terms'",
        (pid,),
    )
    assert person.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).status_code == 201


# --- RF-003: borrador, retirada y versión conservada ---


@pytest.mark.parametrize("status", ["draft", "retired"])
def test_rf003_borrador_o_retirada_no_inician(person, superuser, status):
    key = make_scenario(superuser, status)
    before = counts(superuser)
    response = person.post(
        "/api/v1/sessions", json={**SCENARIO, "scenario_key": key}, headers=WRITE
    )
    assert response.status_code == 404
    assert counts(superuser) == before
    assert key not in [s["key"] for s in person.get("/api/v1/entry").json()["scenarios"]]


def test_rf003_la_sesion_conserva_su_version_al_retirarla(person, superuser):
    key = make_scenario(superuser, "published")
    created = person.post("/api/v1/sessions", json={**SCENARIO, "scenario_key": key}, headers=WRITE)
    assert created.status_code == 201
    sid = created.json()["id"]
    version = superuser.execute(
        "SELECT scenario_version_id FROM nukyro.sessions WHERE id=%s", (sid,)
    ).fetchone()[0]
    superuser.execute(
        "UPDATE nukyro.scenario_versions SET status='retired', retired_at=now() WHERE id=%s",
        (version,),
    )
    assert superuser.execute(
        "SELECT scenario_version_id FROM nukyro.sessions WHERE id=%s", (sid,)
    ).fetchone() == (version,)
    retry = person.post("/api/v1/sessions", json={**SCENARIO, "scenario_key": key}, headers=WRITE)
    assert retry.status_code == 404
    # RF-013: la introducción es la de la versión fijada, aunque salga una versión nueva
    scenario = superuser.execute(
        "SELECT scenario_id FROM nukyro.scenario_versions WHERE id=%s", (version,)
    ).fetchone()[0]
    v2 = superuser.execute(
        "INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title, introduction) "
        "VALUES (%s, 2, %s, 'DEMOSTRACIÓN: introducción NUEVA de la versión 2') RETURNING id",
        (scenario, f"{key} DEMOSTRACIÓN 2"),
    ).fetchone()[0]
    superuser.execute(
        "INSERT INTO nukyro.nodes (version_id, key, node_type, title, body) "
        "VALUES (%s, 'intro', 'intro', 'Inicio', 'Texto de demostración')",
        (v2,),
    )
    superuser.execute(
        "UPDATE nukyro.scenario_versions SET status='published', published_at=now() WHERE id=%s",
        (v2,),
    )
    again = person.get(f"/api/v1/sessions/{sid}")
    assert again.status_code == 200
    assert again.json()["scenario"] == {
        "key": key,
        "title": f"{key} DEMOSTRACIÓN",
        "version_number": 1,
        "introduction": f"DEMOSTRACIÓN: introducción de la versión 1 de {key}",
    }
    assert created.json()["scenario"]["introduction"] == again.json()["scenario"]["introduction"]
    listed = person.get("/api/v1/sessions").json()["sessions"]
    assert [x["scenario"]["introduction"] for x in listed] == [
        f"DEMOSTRACIÓN: introducción de la versión 1 de {key}"
    ]
    fresh = person.post("/api/v1/sessions", json={**SCENARIO, "scenario_key": key}, headers=WRITE)
    assert fresh.status_code == 201 and fresh.json()["scenario"]["version_number"] == 2
    assert "NUEVA" in fresh.json()["scenario"]["introduction"]


def test_rf001_la_sesion_nace_con_variables_y_primer_paso(person, superuser):
    sid = person.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).json()["id"]
    steps = superuser.execute(
        "SELECT seq, n.node_type FROM nukyro.session_steps s "
        "JOIN nukyro.nodes n ON n.id = s.node_id "
        "WHERE s.session_id = %s",
        (sid,),
    ).fetchall()
    assert steps == [(1, "intro")]
    assert superuser.execute(
        "SELECT count(*) FROM nukyro.session_variables WHERE session_id = %s", (sid,)
    ).fetchone() == (3,)
    assert superuser.execute(
        "SELECT p.last_activity_at >= p.created_at FROM nukyro.participants p "
        "JOIN nukyro.sessions s ON s.participant_id = p.id WHERE s.id = %s",
        (sid,),
    ).fetchone() == (True,)


# --- RF-068 y RF-071 ---


def test_rf068_consultar_el_aviso_no_crea_filas(new_client, superuser):
    client = new_client()
    before = counts(superuser)
    response = client.get("/api/v1/entry")
    assert response.status_code == 200 and "set-cookie" not in response.headers
    assert counts(superuser) == before


def test_rf071_el_escenario_sembrado_es_demo_y_la_api_no_escribe_contenido(
    person, superuser, settings, secrets
):
    row = superuser.execute(
        "SELECT s.title, v.title, v.status FROM nukyro.scenarios s "
        "JOIN nukyro.scenario_versions v ON v.scenario_id = s.id WHERE s.key = 'DEMO-BECAS'"
    ).fetchone()
    assert "DEMOSTRACIÓN" in row[0] and "DEMOSTRACIÓN" in row[1] and row[2] == "published"
    api_password = secrets["NUKYRO_DB_API_PASSWORD"]
    with connect(settings, "nukyro_api_app", api_password) as api:
        for sql in (
            "INSERT INTO nukyro.scenarios (key, title) VALUES ('X', 'X')",
            "UPDATE nukyro.nodes SET title = 'x'",
            "DELETE FROM nukyro.state_variables",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                api.execute(sql)
    digest = content_digest(superuser)
    assert person.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).status_code == 201
    assert content_digest(superuser) == digest


# --- RF-062: secretos fuera de los logs ---


def test_rf062_el_secreto_y_la_entrada_no_salen_en_los_logs(person):
    secret = secret_of(person)
    person.post("/api/v1/sessions", json=SCENARIO, headers=WRITE)
    person.post("/api/v1/sessions", json={"scenario_key": "marca-uno"}, headers=WRITE)
    person.get("/api/v1/sessions?q=marca-dos")
    logs = compose("logs", "--no-color", "api", "proxy")
    assert "POST /api/v1/sessions" in logs  # las peticiones sí se registran
    for forbidden in (secret, "marca-uno", "marca-dos"):
        assert forbidden not in logs


# --- Concurrencia y archivo ---


def race(new_client, secret: str) -> list:
    """Dos POST /sessions simultáneos con la misma cookie."""
    results = []
    barrier = threading.Barrier(2)

    def worker():
        http = new_client()
        headers = {**WRITE, "Cookie": f"__Host-nukyro_participant={secret}"}
        barrier.wait()
        results.append(http.post("/api/v1/sessions", json=SCENARIO, headers=headers))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def test_dos_inicios_http_simultaneos_dejan_una_sola_primera_sesion(new_client, superuser):
    for _ in range(5):
        client = new_client()
        client.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
        results = race(new_client, secret_of(client))
        assert [r.status_code for r in results] == [201, 201]
        assert sorted(r.json()["is_first_session"] for r in results) == [False, True]
        pid = participant_id(superuser, client)
        assert superuser.execute(
            "SELECT count(*) FROM nukyro.sessions WHERE participant_id=%s AND is_first_session",
            (pid,),
        ).fetchone() == (1,)


def test_archivo_anonimo_deja_un_hecho_sin_xmin_compartido(person, new_client, superuser):
    other = new_client()  # otro participante vivo: sus filas no deben compartir xmin con los hechos
    other.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
    other.post("/api/v1/sessions", json=SCENARIO, headers=WRITE)
    person.post("/api/v1/sessions", json=SCENARIO, headers=WRITE)
    pid = participant_id(superuser, person)
    facts = superuser.execute("SELECT count(*) FROM nukyro.session_facts").fetchone()[0]
    assert superuser.execute(
        "SELECT nukyro.erase_anonymous_participant(%s)", (pid,)
    ).fetchone() == (True,)
    assert superuser.execute("SELECT count(*) FROM nukyro.session_facts").fetchone()[0] == facts + 1
    shared = superuser.execute(
        "SELECT count(*) FROM nukyro.session_facts f JOIN nukyro.participants p "
        "ON f.xmin::text = p.xmin::text"
    ).fetchone()[0]
    assert shared == 0
    assert superuser.execute(
        "SELECT count(*) FROM nukyro.participants WHERE id=%s", (pid,)
    ).fetchone() == (0,)
