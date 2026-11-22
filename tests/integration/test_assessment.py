# ruff: noqa: E501
"""Evaluaciones y hitos contra la API y la base reales (T-14, RF-005, RF-007 a RF-012, RF-050 a RF-059, RF-061).

Contenido propio: pretest (P1 b, P2 a), posttest (T1 c, T2 a), transferencia (X1 b) y causal
(CE requiere EV, CA requiere OUT_A, CB requiere OUT_B, CN sin condición). D (con justificación)
tiene A (p-2: activa EV, va a OUT_A) y B (p+1, va a OUT_B); R1 es correcta y R2 no.
"""

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from .conftest import ACCEPT, WRITE, participant_id

FORBIDDEN = {"is_correct", "correct", "topic", "objective", "learning_objective", "assesses"}
CORRECT = {
    "P1": "b",
    "P2": "a",
    "T1": "c",
    "T2": "a",
    "X1": "b",
    "CE": "a",
    "CA": "a",
    "CB": "a",
    "CN": "a",
}


def build(superuser, *, finals=True, lenient=False):
    key = f"T14-{uuid.uuid4().hex[:8]}"
    ex = superuser.execute
    sid = ex(
        "INSERT INTO nukyro.scenarios (key, title) VALUES (%s, %s) RETURNING id", (key, key)
    ).fetchone()[0]
    v = ex(
        "INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title) VALUES (%s, 1, %s) RETURNING id",
        (sid, f"{key} DEMOSTRACIÓN"),
    ).fetchone()[0]
    lo = ex(
        "INSERT INTO nukyro.learning_objectives (version_id, key, description) VALUES (%s,'LO','x') RETURNING id",
        (v,),
    ).fetchone()[0]
    ex(
        "INSERT INTO nukyro.state_variables (version_id, key, label, initial_value, min_value, max_value) "
        "VALUES (%s,'p','P',3,0,5)",
        (v,),
    )
    ids = {}
    for k, t in (
        ("intro", "intro"),
        ("D", "decision"),
        ("EV", "event"),
        ("OUT_A", "outcome"),
        ("OUT_B", "outcome"),
    ):
        ids[k] = ex(
            "INSERT INTO nukyro.nodes (version_id, key, node_type, title, body) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (v, k, t, f"Título {k}", f"Texto {k}"),
        ).fetchone()[0]
    for k, nxt in (("intro", "D"), ("D", "OUT_A")):
        ex("UPDATE nukyro.nodes SET default_next_node_id=%s WHERE id=%s", (ids[nxt], ids[k]))
    ex(
        "INSERT INTO nukyro.decision_points (node_id, version_id, requires_justification, learning_objective_id, "
        "affected_parties) VALUES (%s, %s, true, %s, 'x')",
        (ids["D"], v, lo),
    )
    for k, eff, nxt in (("A", -2, None), ("B", 1, ids["OUT_B"])):
        ex(
            "INSERT INTO nukyro.options (version_id, node_id, key, label, effects, next_node_id) VALUES (%s,%s,%s,%s,%s,%s)",
            (
                v,
                ids["D"],
                k,
                f"Alternativa {k}",
                json.dumps([{"variable_key": "p", "op": "add", "value": eff}]),
                nxt,
            ),
        )
    for k, ok in (("R1", True), ("R2", False)):
        ex(
            "INSERT INTO nukyro.justification_reasons (version_id, node_id, key, label, is_correct) VALUES (%s,%s,%s,%s,%s)",
            (v, ids["D"], k, f"Razón {k}", ok),
        )
    ex(
        "INSERT INTO nukyro.rules (version_id, key, rule_type, from_node_id, condition, target_node_id, relation_type, "
        "priority, explanation) VALUES (%s,'RULE-EV','event',%s,%s,%s,'causal',100,'x')",
        (v, ids["D"], json.dumps({"var": "p", "op": "lt", "value": 2}), ids["EV"]),
    )

    def qset(kind, questions, all_answers=True):
        st = ex(
            "INSERT INTO nukyro.question_sets (version_id, set_type, requires_all_answers) VALUES (%s,%s,%s) RETURNING id",
            (v, kind, all_answers),
        ).fetchone()[0]
        for pos, (qk, requires) in enumerate(questions):
            q = ex(
                "INSERT INTO nukyro.questions (version_id, question_set_id, key, prompt, topic, learning_objective_id, "
                "requires_node_id, position) VALUES (%s,%s,%s,%s,'tema secreto',%s,%s,%s) RETURNING id",
                (v, st, qk, f"Enunciado {qk}", lo, ids.get(requires), pos),
            ).fetchone()[0]
            for ok in "abc":
                ex(
                    "INSERT INTO nukyro.question_options (version_id, question_id, key, label, is_correct, position) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (v, q, ok, f"Opción {ok} de {qk}", ok == CORRECT[qk], "abc".index(ok)),
                )

    qset("pretest", [("P1", None), ("P2", None)], all_answers=not lenient)
    if finals:
        qset("posttest", [("T1", None), ("T2", None)])
        qset("transfer", [("X1", None)])
        qset("causal", [("CE", "EV"), ("CA", "OUT_A"), ("CB", "OUT_B"), ("CN", None)])
    ex(
        "UPDATE nukyro.scenario_versions SET status='published', published_at=now() WHERE id=%s",
        (v,),
    )
    return key


@pytest.fixture(scope="module")
def full(superuser):
    return build(superuser)


@pytest.fixture(scope="module")
def plain(superuser):
    return build(superuser, finals=False)


@pytest.fixture(scope="module")
def lenient(superuser):
    return build(superuser, lenient=True)


def start(client, key) -> str:
    r = client.post(
        "/api/v1/sessions", headers=WRITE, json={"scenario_key": key, "self_reported_first": True}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def url(sid, kind, *rest) -> str:
    return "/".join(["/api/v1/sessions", sid, "assessments", kind, *rest])


def answer(client, sid, kind, question, option):
    return client.put(
        url(sid, kind, "answers", question), json={"option_key": option}, headers=WRITE
    )


def submit(client, sid, kind):
    return client.post(url(sid, kind, "submit"), headers=WRITE)


def fill(client, sid, kind, picks):
    for q, o in picks.items():
        assert answer(client, sid, kind, q, o).status_code == 200


def at_pretest_done(client, key, picks=None) -> str:
    sid = start(client, key)
    fill(client, sid, "pretest", picks or {"P1": "b", "P2": "a"})
    assert submit(client, sid, "pretest").status_code == 200
    return sid


def finish(client, sid, option="A", reasons=("R1",)) -> None:
    adv = client.post(
        f"/api/v1/sessions/{sid}/advance", json={"from_node_key": "intro"}, headers=WRITE
    )
    assert adv.status_code == 200, adv.text
    body = {"node_key": "D", "option_key": option, "reason_keys": list(reasons)}
    assert (
        client.post(f"/api/v1/sessions/{sid}/decisions", json=body, headers=WRITE).status_code
        == 200
    )


def row(db, sql, *params):
    return db.execute(sql, params).fetchone()


def keys(value) -> set:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


# --- RF-007 y RF-008 ------------------------------------------------------------------------


def test_rf007_rf008_con_la_sesion_iniciada_se_ven_las_preguntas_del_pretest_sin_correctas(
    person, full
):
    sid = start(person, full)
    r = person.get(url(sid, "pretest"))
    assert r.status_code == 200
    data = r.json()
    assert (data["type"], data["submitted"], data["answered"], data["total"], data["score"]) == (
        "pretest",
        False,
        0,
        2,
        None,
    )
    assert [q["key"] for q in data["questions"]] == ["P1", "P2"]  # por posición
    assert sorted(o["key"] for o in data["questions"][0]["options"]) == ["a", "b", "c"]
    assert not keys(data) & FORBIDDEN
    assert "tema secreto" not in r.text and "Opción" in r.text


def test_rf008_el_orden_de_las_opciones_es_fijo_por_sesion_y_cambia_entre_sesiones(person, full):
    orders = set()
    for _ in range(5):
        sid = start(person, full)
        first = person.get(url(sid, "pretest")).json()
        assert first == person.get(url(sid, "pretest")).json()
        orders.add(tuple(o["key"] for q in first["questions"] for o in q["options"]))
    assert len(orders) > 1


def test_rf007_una_sesion_ajena_es_404_en_las_tres_rutas(person, new_client, full):
    sid = start(person, full)
    other = new_client()
    other.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
    assert other.get(url(sid, "pretest")).status_code == 404
    assert answer(other, sid, "pretest", "P1", "b").status_code == 404
    assert submit(other, sid, "pretest").status_code == 404
    assert person.get(url(sid, "inexistente")).status_code == 404
    assert person.get(url("no-es-uuid", "pretest")).status_code == 404


# --- RF-009 y RF-010 -------------------------------------------------------------------------


def test_rf009_rf010_una_respuesta_por_pregunta_modificable_antes_de_enviar(
    person, superuser, full
):
    sid = start(person, full)
    assert answer(person, sid, "pretest", "P1", "a").json() == {
        "answered": 1,
        "total": 2,
        "submitted": False,
    }
    assert answer(person, sid, "pretest", "P1", "c").json()["answered"] == 1  # cambia, no suma
    got = person.get(url(sid, "pretest")).json()
    assert [q["selected_option_key"] for q in got["questions"]] == ["c", None]
    assert (
        row(
            superuser,
            "SELECT count(*) FROM nukyro.assessment_answers a JOIN nukyro.assessment_attempts t ON t.id = a.attempt_id WHERE t.session_id = %s",
            sid,
        )[0]
        == 1
    )


def test_rf009_rf010_rechazos_no_cambian_nada(person, superuser, full):
    sid = start(person, full)
    fill(person, sid, "pretest", {"P1": "a"})
    count = "SELECT count(*), max(a.option_id::text) FROM nukyro.assessment_answers a JOIN nukyro.assessment_attempts t ON t.id = a.attempt_id WHERE t.session_id = %s"
    before = row(superuser, count, sid)
    assert answer(person, sid, "pretest", "P1", "z").status_code == 422  # opción inexistente
    assert answer(person, sid, "pretest", "P9", "a").status_code == 422  # pregunta inexistente
    assert answer(person, sid, "pretest", "T1", "a").status_code == 422  # pregunta de otro conjunto
    assert (
        person.put(
            url(sid, "pretest", "answers", "P1"), json={"option_key": "a", "x": 1}, headers=WRITE
        ).status_code
        == 422
    )
    assert row(superuser, count, sid) == before
    fill(person, sid, "pretest", {"P2": "a"})
    assert submit(person, sid, "pretest").status_code == 200
    after = row(superuser, count, sid)
    assert answer(person, sid, "pretest", "P1", "b").status_code == 409  # tras enviar
    assert row(superuser, count, sid) == after


def test_la_escritura_sin_csrf_es_403(person, full):
    sid = start(person, full)
    assert (
        person.put(url(sid, "pretest", "answers", "P1"), json={"option_key": "a"}).status_code
        == 403
    )
    assert person.post(url(sid, "pretest", "submit")).status_code == 403


# --- RF-011 ---------------------------------------------------------------------------------


def test_rf011_el_porcentaje_es_el_calculado_a_mano(person, superuser, full):
    sid = at_pretest_done(person, full, {"P1": "b", "P2": "c"})  # 1 de 2
    got = person.get(url(sid, "pretest")).json()
    assert got["submitted"] is True and got["score"] is None  # no sale antes de terminar
    assert row(
        superuser,
        "SELECT answered_count, correct_count, score FROM nukyro.assessment_attempts WHERE session_id = %s",
        sid,
    ) == (2, 1, 50)


def test_rf011_incompleto_que_exige_todas_es_409_sin_puntuacion(person, superuser, full):
    sid = start(person, full)
    fill(person, sid, "pretest", {"P1": "b"})
    assert submit(person, sid, "pretest").status_code == 409
    assert row(
        superuser,
        "SELECT submitted_at, score FROM nukyro.assessment_attempts WHERE session_id = %s",
        sid,
    ) == (None, None)
    assert (
        row(superuser, "SELECT pretest_completed_at FROM nukyro.sessions WHERE id = %s", sid)[0]
        is None
    )


def test_rf011_si_no_exige_todas_el_porcentaje_es_sobre_las_respondidas(person, superuser, lenient):
    sid = start(person, lenient)
    fill(person, sid, "pretest", {"P1": "b"})
    assert submit(person, sid, "pretest").json()["score"] is None
    assert (
        row(
            superuser,
            "SELECT t.score::float FROM nukyro.assessment_attempts t JOIN nukyro.question_sets q ON q.id = t.question_set_id WHERE t.session_id = %s AND q.set_type = 'pretest'",
            sid,
        )[0]
        == 100.0
    )  # 1 de 1 respondidas


def test_rf011_cero_respondidas_no_puntua(person, superuser, lenient):
    sid = start(person, lenient)
    r = submit(person, sid, "pretest")
    assert r.status_code == 200 and r.json()["score"] is None and r.json()["submitted"] is True
    assert row(
        superuser,
        "SELECT answered_count, score FROM nukyro.assessment_attempts WHERE session_id = %s",
        sid,
    ) == (0, None)


def test_rf011_enviar_dos_veces_devuelve_lo_mismo_y_no_recalifica(person, superuser, full):
    sid = at_pretest_done(person, full, {"P1": "b", "P2": "a"})
    first = row(
        superuser,
        "SELECT submitted_at, score, pretest_completed_at FROM nukyro.assessment_attempts t JOIN nukyro.sessions s ON s.id = t.session_id WHERE s.id = %s",
        sid,
    )
    again = submit(person, sid, "pretest")
    assert again.status_code == 200 and again.json() == person.get(url(sid, "pretest")).json()
    assert again.json()["score"] is None and float(first[1]) == 100.0
    assert (
        row(
            superuser,
            "SELECT submitted_at, score, pretest_completed_at FROM nukyro.assessment_attempts t JOIN nukyro.sessions s ON s.id = t.session_id WHERE s.id = %s",
            sid,
        )
        == first
    )


def test_rf011_envios_simultaneos_dejan_un_solo_intento_enviado(person, superuser, full):
    sid = start(person, full)
    fill(person, sid, "pretest", {"P1": "b", "P2": "a"})
    barrier = threading.Barrier(6)

    def go(_):
        barrier.wait()
        return submit(person, sid, "pretest")

    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(go, range(6)))
    assert {r.status_code for r in results} == {200}
    assert len({json.dumps(r.json(), sort_keys=True) for r in results}) == 1
    assert (
        row(
            superuser, "SELECT count(*) FROM nukyro.assessment_attempts WHERE session_id = %s", sid
        )[0]
        == 1
    )


# --- RF-012 y RF-055 ---------------------------------------------------------------------------


def test_rf012_rf055_cada_intento_queda_en_su_sesion(person, superuser, full):
    one = start(person, full)
    two = start(person, full)
    fill(person, one, "pretest", {"P1": "a"})
    assert [
        q["selected_option_key"] for q in person.get(url(two, "pretest")).json()["questions"]
    ] == [None, None]
    fill(person, two, "pretest", {"P1": "c"})
    assert [
        q["selected_option_key"] for q in person.get(url(one, "pretest")).json()["questions"]
    ] == ["a", None]
    assert (
        row(
            superuser,
            "SELECT count(DISTINCT session_id) FROM nukyro.assessment_attempts WHERE session_id IN (%s, %s)",
            one,
            two,
        )[0]
        == 2
    )


# --- Orden y hitos (RF-005, RF-050 a RF-054) -------------------------------------------------------


def test_rf008_sin_enviar_el_pretest_no_se_sale_del_primer_nodo(person, full):
    sid = start(person, full)
    adv = person.post(
        f"/api/v1/sessions/{sid}/advance", json={"from_node_key": "intro"}, headers=WRITE
    )
    assert adv.status_code == 409
    fill(person, sid, "pretest", {"P1": "b", "P2": "a"})
    assert submit(person, sid, "pretest").status_code == 200
    adv = person.post(
        f"/api/v1/sessions/{sid}/advance", json={"from_node_key": "intro"}, headers=WRITE
    )
    assert adv.status_code == 200 and adv.json()["state"] == "in_scenario"
    assert [p["phase"] for p in adv.json()["phases"]] == ["started", "in_scenario"]


def test_rf050_antes_del_desenlace_ningun_conjunto_final_es_409(person, full):
    sid = at_pretest_done(person, full)
    for kind in ("posttest", "transfer", "causal"):
        assert person.get(url(sid, kind)).status_code == 409
        assert answer(person, sid, kind, "T1", "c").status_code == 409
        assert submit(person, sid, kind).status_code == 409


def test_rf050_rf051_rf052_rf058_el_orden_es_posttest_transferencia_causal(person, superuser, full):
    sid = at_pretest_done(person, full)
    finish(person, sid, "A")
    assert person.get(url(sid, "transfer")).status_code == 409  # antes de su turno
    assert person.get(url(sid, "causal")).status_code == 409
    assert row(superuser, "SELECT completed_at FROM nukyro.sessions WHERE id = %s", sid)[0] is None
    fill(person, sid, "posttest", {"T1": "c", "T2": "b"})  # 1 de 2
    r = submit(person, sid, "posttest")
    assert r.status_code == 200 and r.json()["score"] is None
    assert (
        row(
            superuser,
            "SELECT t.score::float FROM nukyro.assessment_attempts t JOIN nukyro.question_sets q ON q.id = t.question_set_id WHERE t.session_id = %s AND q.set_type = 'posttest'",
            sid,
        )[0]
        == 50.0
    )
    assert person.get(url(sid, "causal")).status_code == 409  # falta transferencia
    fill(person, sid, "transfer", {"X1": "b"})
    assert submit(person, sid, "transfer").json()["score"] is None
    assert (
        row(
            superuser,
            "SELECT t.score::float FROM nukyro.assessment_attempts t JOIN nukyro.question_sets q ON q.id = t.question_set_id WHERE t.session_id = %s AND q.set_type = 'transfer'",
            sid,
        )[0]
        == 100.0
    )
    assert row(superuser, "SELECT completed_at FROM nukyro.sessions WHERE id = %s", sid)[0] is None
    # Recorrido A: EV activado y OUT_A; CB (OUT_B) no ocurrió
    causal = person.get(url(sid, "causal")).json()
    assert [q["key"] for q in causal["questions"]] == ["CE", "CA", "CN"]
    count = "SELECT count(*) FROM nukyro.assessment_answers a JOIN nukyro.assessment_attempts t ON t.id = a.attempt_id WHERE t.session_id = %s"
    before = row(superuser, count, sid)[0]
    assert answer(person, sid, "causal", "CB", "a").status_code == 422  # no ocurrida: no se acepta
    assert row(superuser, count, sid)[0] == before
    fill(person, sid, "causal", {"CE": "a", "CA": "b"})
    assert submit(person, sid, "causal").status_code == 409  # exige todas
    fill(person, sid, "causal", {"CN": "a"})
    done = submit(person, sid, "causal")
    assert done.json()["score"] == 66.67  # 2 de 3
    state = person.get(f"/api/v1/sessions/{sid}").json()
    assert state["state"] == "completed"
    assert [p["phase"] for p in state["phases"]] == [
        "started",
        "in_scenario",
        "outcome_reached",
        "completed",
    ]
    h = row(
        superuser,
        "SELECT pretest_completed_at <= outcome_reached_at AND outcome_reached_at <= completed_at, outcome_node_id IS NOT NULL FROM nukyro.sessions WHERE id = %s",
        sid,
    )
    assert h == (True, True)


def test_rf058_el_recorrido_b_ofrece_su_desenlace_y_no_el_evento_que_no_ocurrio(person, full):
    sid = at_pretest_done(person, full)
    finish(person, sid, "B", ("R1",))
    fill(person, sid, "posttest", {"T1": "c", "T2": "a"})
    submit(person, sid, "posttest")
    fill(person, sid, "transfer", {"X1": "b"})
    submit(person, sid, "transfer")
    assert [q["key"] for q in person.get(url(sid, "causal")).json()["questions"]] == ["CB", "CN"]
    assert answer(person, sid, "causal", "CE", "a").status_code == 422
    assert answer(person, sid, "causal", "CA", "a").status_code == 422


def test_una_version_sin_conjuntos_finales_se_completa_al_llegar_al_desenlace(
    person, superuser, plain
):
    sid = at_pretest_done(person, plain)
    assert row(superuser, "SELECT completed_at FROM nukyro.sessions WHERE id = %s", sid)[0] is None
    finish(person, sid)
    assert person.get(f"/api/v1/sessions/{sid}").json()["state"] == "completed"
    assert person.get(url(sid, "posttest")).status_code == 404  # la versión no lo tiene


def test_rf011_un_pretest_enviado_no_se_vuelve_a_abrir_ni_cambia_el_hito(person, superuser, full):
    sid = at_pretest_done(person, full)
    hito = row(superuser, "SELECT pretest_completed_at FROM nukyro.sessions WHERE id = %s", sid)[0]
    assert answer(person, sid, "pretest", "P1", "a").status_code == 409
    submit(person, sid, "pretest")
    assert (
        row(superuser, "SELECT pretest_completed_at FROM nukyro.sessions WHERE id = %s", sid)[0]
        == hito
    )


# --- Actividad (RF-080) y defecto 10 -----------------------------------------------------------------


def test_las_escrituras_aceptadas_renuevan_la_actividad_y_las_rechazadas_no(
    person, superuser, full
):
    sid = start(person, full)
    pid = participant_id(superuser, person)
    old = "UPDATE nukyro.{} SET last_activity_at = now() - interval '2 days' WHERE id = %s"
    probe = "SELECT (SELECT last_activity_at FROM nukyro.participants WHERE id = %s) > now() - interval '1 day', (SELECT last_activity_at FROM nukyro.sessions WHERE id = %s) > now() - interval '1 day'"
    superuser.execute(old.format("participants"), (pid,))
    superuser.execute(old.format("sessions"), (sid,))
    assert answer(person, sid, "pretest", "P1", "z").status_code == 422
    assert row(superuser, probe, pid, sid) == (False, False)
    assert answer(person, sid, "pretest", "P1", "a").status_code == 200
    assert row(superuser, probe, pid, sid) == (True, True)


def test_defecto_10_marcar_todas_las_razones_no_aprueba_la_justificacion(person, superuser, full):
    """Con la regla vieja (solo el mínimo de correctas) marcar R1 y R2 aprobaba."""
    todas = at_pretest_done(person, full)
    finish(person, todas, "A", ("R1", "R2"))
    buena = at_pretest_done(person, full)
    finish(person, buena, "A", ("R1",))
    q = "SELECT justification_correct FROM nukyro.session_decisions WHERE session_id = %s"
    assert row(superuser, q, todas)[0] is False
    assert row(superuser, q, buena)[0] is True
