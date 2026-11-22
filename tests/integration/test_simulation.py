# ruff: noqa: E501
"""Motor y persistencia P5 contra la API y la base reales (T-07).

Contenido propio con los ejemplos de ADR-009. El pre-test se marca desde la preparación (E4 lo califica).
"""

import hashlib
import json
import secrets as pysecrets
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from nukyro.db import make_engine
from nukyro.modules.simulation import queries, service
from nukyro.modules.simulation.schemas import AdvanceIn, DecisionIn

from .conftest import ACCEPT, WRITE

SESSION_TABLES = (
    "session_steps",
    "session_decisions",
    "session_decision_reasons",
    "session_effects",
    "session_events",
    "session_event_causes",
)


@pytest.fixture(scope="module")
def content(superuser):
    """ADR-009: p y e entre 0 y 5; D1 (A, B con razones); D2 (C, D); EV; MALO y BUENO."""
    key = f"T07-{uuid.uuid4().hex[:8]}"
    ex = superuser.execute
    sid = ex(
        "INSERT INTO nukyro.scenarios (key, title) VALUES (%s, %s) RETURNING id", (key, key)
    ).fetchone()[0]
    v = ex(
        "INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title) "
        "VALUES (%s, 1, %s) RETURNING id",
        (sid, f"{key} DEMOSTRACIÓN"),
    ).fetchone()[0]
    ex(
        "INSERT INTO nukyro.learning_objectives (version_id, key, description) VALUES (%s,'LO','x')",
        (v,),
    )
    ex(
        "INSERT INTO nukyro.state_variables (version_id, key, label, initial_value, min_value, max_value) "
        "VALUES (%s,'p','P',3,0,5), (%s,'e','E',3,0,5)",
        (v, v),
    )
    ids = {}
    for k, t in (
        ("intro", "intro"),
        ("D1", "decision"),
        ("D2", "decision"),
        ("EV", "event"),
        ("MALO", "outcome"),
        ("BUENO", "outcome"),
    ):
        ids[k] = ex(
            "INSERT INTO nukyro.nodes (version_id, key, node_type, title, body) "
            "VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (v, k, t, f"Título {k}", f"Texto narrativo {k}"),
        ).fetchone()[0]
    for k, nxt in (("intro", "D1"), ("D1", "D2"), ("D2", "BUENO")):
        ex("UPDATE nukyro.nodes SET default_next_node_id=%s WHERE id=%s", (ids[nxt], ids[k]))
    ex(
        "INSERT INTO nukyro.decision_points (node_id, version_id, requires_justification, "
        "learning_objective_id, affected_parties) SELECT %s, %s, true, id, 'x' "
        "FROM nukyro.learning_objectives WHERE version_id=%s",
        (ids["D1"], v, v),
    )
    ex(
        "INSERT INTO nukyro.decision_points (node_id, version_id, learning_objective_id, "
        "affected_parties) SELECT %s, %s, id, 'x' FROM nukyro.learning_objectives "
        "WHERE version_id=%s",
        (ids["D2"], v, v),
    )
    for node, k, eff in (("D1", "A", -2), ("D1", "B", 3), ("D2", "C", 1), ("D2", "D", -2)):
        var = "e" if k == "C" else "p"
        ex(
            "INSERT INTO nukyro.options (version_id, node_id, key, label, effects) "
            "VALUES (%s,%s,%s,%s,%s)",
            (
                v,
                ids[node],
                k,
                f"Alternativa {k}",
                json.dumps([{"variable_key": var, "op": "add", "value": eff}]),
            ),
        )
    for k, ok in (("R1", True), ("R2", False)):
        ex(
            "INSERT INTO nukyro.justification_reasons (version_id, node_id, key, label, is_correct) "
            "VALUES (%s,%s,%s,%s,%s)",
            (v, ids["D1"], k, f"Razón {k}", ok),
        )
    for rk, typ, cond, target, prio in (
        ("RULE-EV", "event", {"var": "p", "op": "lt", "value": 2}, "EV", 100),
        (
            "RULE-MALO",
            "transition",
            {"any": [{"var": "p", "op": "lte", "value": 1}, {"chose": "D"}]},
            "MALO",
            10,
        ),
    ):
        ex(
            "INSERT INTO nukyro.rules (version_id, key, rule_type, from_node_id, condition, "
            "target_node_id, relation_type, priority, explanation) "
            "VALUES (%s,%s,%s,%s,%s,%s,'causal',%s,'Explicación interna')",
            (v, rk, typ, ids["D2"], json.dumps(cond), ids[target], prio),
        )
    ex("INSERT INTO nukyro.question_sets (version_id, set_type) VALUES (%s,'pretest')", (v,))
    ex(
        "UPDATE nukyro.scenario_versions SET status='published', published_at=now() WHERE id=%s",
        (v,),
    )
    return {"key": key, "version": v}


def new_session(client, content, superuser, pretest=True) -> str:
    r = client.post(
        "/api/v1/sessions",
        headers=WRITE,
        json={"scenario_key": content["key"], "self_reported_first": True},
    )
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    if pretest:
        superuser.execute(
            "UPDATE nukyro.sessions SET pretest_completed_at = now() WHERE id=%s", (sid,)
        )
    return sid


def advance(client, sid, node):
    return client.post(
        f"/api/v1/sessions/{sid}/advance", json={"from_node_key": node}, headers=WRITE
    )


def decide(client, sid, node, option, reasons=()):
    return client.post(
        f"/api/v1/sessions/{sid}/decisions",
        headers=WRITE,
        json={"node_key": node, "option_key": option, "reason_keys": list(reasons)},
    )


def snapshot(db, sid):
    parts = [
        db.execute(
            f"SELECT count(*) FROM nukyro.{t} "
            f"WHERE {'session_id' if t != 'session_decision_reasons' else 'session_decision_id'}"
            + (
                " IN (SELECT id FROM nukyro.session_decisions WHERE session_id=%s)"
                if t == "session_decision_reasons"
                else "=%s"
            ),
            (sid,),
        ).fetchone()[0]
        for t in SESSION_TABLES
    ]
    parts.append(
        db.execute(
            "SELECT (SELECT md5(s::text) FROM nukyro.sessions s WHERE id=%s), "
            "(SELECT md5(string_agg(v::text, '|' ORDER BY variable_id)) "
            "FROM nukyro.session_variables v WHERE session_id=%s)",
            (sid, sid),
        ).fetchone()
    )
    return parts


PATHS = [  # (alternativas, p, e, evento, final, causas del evento, causas de la transición)
    (("A", "C"), 1, 4, True, "MALO", {"D1"}, {"D1"}),
    (("A", "D"), 0, 3, True, "MALO", {"D1", "D2"}, {"D1", "D2"}),
    (("B", "C"), 5, 4, False, "BUENO", set(), set()),
    (("B", "D"), 3, 3, False, "MALO", set(), {"D2"}),
]


@pytest.mark.parametrize("path,p,e,event,final,ev_causes,tr_causes", PATHS)
def test_rf064_cuatro_recorridos_persisten_valores_causas_y_final(
    person, superuser, content, path, p, e, event, final, ev_causes, tr_causes
):
    sid = new_session(person, content, superuser)
    assert advance(person, sid, "intro").status_code == 200
    assert decide(person, sid, "D1", path[0], ["R1"]).status_code == 200
    last = decide(person, sid, "D2", path[1])
    assert last.status_code == 200 and last.json()["replayed"] is False
    view = last.json()["session"]
    assert view["current_node"]["key"] == final and view["state"] == "outcome_reached"
    assert [x["title"] for x in view["events"]] == (["Título EV"] if event else [])
    values = dict(
        superuser.execute(
            "SELECT v.key, sv.value FROM nukyro.session_variables sv JOIN nukyro.state_variables v "
            "ON v.id=sv.variable_id WHERE sv.session_id=%s",
            (sid,),
        ).fetchall()
    )
    assert values == {"p": p, "e": e}
    causes = {}
    for rule, node in superuser.execute(
        "SELECT r.key, n.key FROM nukyro.session_events ev JOIN nukyro.rules r ON r.id=ev.rule_id "
        "LEFT JOIN nukyro.session_event_causes c ON c.session_event_id=ev.id "
        "LEFT JOIN nukyro.session_decisions d ON d.id=c.session_decision_id "
        "LEFT JOIN nukyro.nodes n ON n.id=d.node_id WHERE ev.session_id=%s",
        (sid,),
    ).fetchall():
        causes.setdefault(rule, set()).update({node} - {None})
    assert causes.get("RULE-EV") == (ev_causes if event else None)
    assert causes.get("RULE-MALO") == (tr_causes if final == "MALO" else None)
    assert superuser.execute(
        "SELECT n.key, s.outcome_reached_at IS NOT NULL FROM nukyro.sessions s "
        "JOIN nukyro.nodes n ON n.id=s.outcome_node_id WHERE s.id=%s",
        (sid,),
    ).fetchone() == (final, True)
    assert snapshot(superuser, sid)[0] == 4  # intro, D1, D2 y el final


def test_defecto1_reintento_tras_avanzar_con_otra_alternativa_devuelve_lo_confirmado(
    person, superuser, content
):
    sid = new_session(person, content, superuser)
    advance(person, sid, "intro")
    assert decide(person, sid, "D1", "A", ["R1"]).status_code == 200
    assert decide(person, sid, "D2", "C").status_code == 200
    before = snapshot(superuser, sid)
    again = decide(person, sid, "D1", "B", ["R2"])
    assert again.status_code == 200
    body = again.json()
    assert body["replayed"] is True and body["confirmed"]["option_key"] == "A"
    assert body["confirmed"]["reason_keys"] == ["R1"]
    assert snapshot(superuser, sid) == before
    assert advance(person, sid, "intro").status_code == 200  # ya salió: estado actual
    assert snapshot(superuser, sid) == before


def test_cada_invalido_deja_cero_cambios(person, new_client, superuser, content):
    sid = new_session(person, content, superuser)
    late = new_session(person, content, superuser, pretest=False)
    assert advance(person, late, "intro").status_code == 409  # pre-test sin completar
    assert decide(person, sid, "D1", "A", ["R1"]).status_code == 409  # aún en intro
    assert advance(person, sid, "NOPE").status_code == 422
    assert advance(person, sid, "intro").status_code == 200
    base = snapshot(superuser, sid)
    bad = [
        (decide(person, sid, "D2", "C"), 409),  # no es el nodo actual
        (decide(person, sid, "D1", "Z", ["R1"]), 422),
        (decide(person, sid, "D1", "A"), 422),  # falta razón
        (decide(person, sid, "D1", "A", ["R1", "R1"]), 422),
        (decide(person, sid, "D1", "A", ["R9"]), 422),
        (decide(person, sid, "XX", "A", ["R1"]), 422),
        (advance(person, sid, "D1"), 409),  # decisión pendiente
        (
            person.post(
                f"/api/v1/sessions/{sid}/decisions",
                headers=WRITE,
                json={"node_key": "D1", "option_key": "A", "reason_keys": ["R1"], "x": 1},
            ),
            422,
        ),
        (
            person.post(
                f"/api/v1/sessions/{sid}/decisions",
                headers=WRITE,
                json={"node_key": 1, "option_key": "A", "reason_keys": []},
            ),
            422,
        ),
        (person.post(f"/api/v1/sessions/{sid}/advance", headers=WRITE, json={}), 422),
        (
            person.post(
                "/api/v1/sessions/no-es-uuid/advance",
                headers=WRITE,
                json={"from_node_key": "intro"},
            ),
            404,
        ),
        (
            new_client().post(
                f"/api/v1/sessions/{sid}/advance", headers=WRITE, json={"from_node_key": "intro"}
            ),
            401,
        ),
    ]
    for r, status in bad:
        assert r.status_code == status, (r.request.url, r.text)
    assert snapshot(superuser, sid) == base
    assert decide(person, sid, "D1", "A", ["R1"]).status_code == 200
    # decisión sin pedir razones: ninguna permitida
    assert decide(person, sid, "D2", "C", ["R1"]).status_code == 422
    assert advance(person, sid, "D2").status_code == 409


def test_el_error_no_refleja_la_entrada(person, superuser, content):
    sid = new_session(person, content, superuser)
    r = decide(person, sid, "SECRETO-REFLEJADO", "OTRO-REFLEJADO", ["R-REFLEJADA"])
    assert "REFLEJAD" not in r.text and "SECRETO" not in r.text


def test_sesion_ajena_es_404_y_no_cambia_nada(person, new_client, superuser, content):
    sid = new_session(person, content, superuser)
    other = new_client()
    other.post(
        "/api/v1/participants",
        json={"age_confirmed": True, "privacy_notice_version": "DEMO-1", "terms_version": "DEMO-1"},
        headers=WRITE,
    )
    base = snapshot(superuser, sid)
    for r in (
        other.get(f"/api/v1/sessions/{sid}"),
        advance(other, sid, "intro"),
        decide(other, sid, "D1", "A", ["R1"]),
    ):
        assert r.status_code == 404
    assert snapshot(superuser, sid) == base
    assert other.get(f"/api/v1/sessions/{uuid.uuid4()}").status_code == 404


def keys_of(x, found=None):
    found = set() if found is None else found
    if isinstance(x, dict):
        for k, v in x.items():
            found.add(k)
            keys_of(v, found)
    elif isinstance(x, list):
        for v in x:
            keys_of(v, found)
    return found


def test_las_respuestas_no_traen_nada_interno(person, superuser, content):
    sid = new_session(person, content, superuser)
    responses = [person.get(f"/api/v1/sessions/{sid}"), advance(person, sid, "intro")]
    got = person.get(f"/api/v1/sessions/{sid}").json()
    assert [o["key"] for o in got["options"]] == ["A", "B"]
    assert [r["key"] for r in got["reasons"]] == ["R1", "R2"]
    responses += [decide(person, sid, "D1", "A", ["R1"]), decide(person, sid, "D2", "D")]
    responses.append(person.get(f"/api/v1/sessions/{sid}"))
    allowed = {
        "id",
        "scenario",
        "key",
        "title",
        "version_number",
        "started_at",
        "is_first_session",
        "state",
        "current_node",
        "type",
        "body",
        "options",
        "reasons",
        "events",
        "label",
        "replayed",
        "confirmed",
        "node_key",
        "option_key",
        "reason_keys",
        "session",
    }
    for r in responses:
        assert r.status_code == 200
        assert keys_of(r.json()) <= allowed, keys_of(r.json()) - allowed
        text = r.text
        for secret in (
            "RULE-",
            "Explicación interna",
            "is_correct",
            "effects",
            "condition",
            "next_node",
            "correct",
            "priority",
            '"p"',
            "relation",
        ):
            assert secret not in text, secret
    final = responses[-1].json()
    assert final["events"] == [{"title": "Título EV", "body": "Texto narrativo EV"}]


# --- Servicio directo: concurrencia y fallos inyectados ---


@pytest.fixture(scope="module")
def api_engine(settings):
    engine = make_engine(settings, "api")
    yield engine
    engine.dispose()


def direct_session(db, content):
    secret = pysecrets.token_hex(16)
    pid = db.execute(
        "INSERT INTO nukyro.participants (secret_hash) VALUES (%s) RETURNING id",
        (hashlib.sha256(secret.encode()).digest(),),
    ).fetchone()[0]
    v = content["version"]
    intro = db.execute(
        "SELECT id FROM nukyro.nodes WHERE version_id=%s AND key='intro'", (v,)
    ).fetchone()[0]
    sid = db.execute(
        "INSERT INTO nukyro.sessions (participant_id, scenario_version_id, current_node_id, "
        "self_reported_first, pretest_completed_at) VALUES (%s,%s,%s,true,now()) RETURNING id",
        (pid, v, intro),
    ).fetchone()[0]
    db.execute(
        "INSERT INTO nukyro.session_variables (session_id, scenario_version_id, variable_id, value) "
        "SELECT %s, %s, id, initial_value FROM nukyro.state_variables WHERE version_id=%s",
        (sid, v, v),
    )
    db.execute(
        "INSERT INTO nukyro.session_steps (session_id, scenario_version_id, node_id, seq) "
        "VALUES (%s,%s,%s,1)",
        (sid, v, intro),
    )
    return secret, str(sid)


def test_mil_pares_concurrentes_no_duplican_nada(api_engine, superuser, content):
    sessions = [direct_session(superuser, content) for _ in range(1000)]

    def adv(s):
        return service.advance(api_engine, s[0], s[1], AdvanceIn(from_node_key="intro"))

    def dec(s):
        return service.decide(
            api_engine, s[0], s[1], DecisionIn(node_key="D1", option_key="A", reason_keys=["R1"])
        )

    with ThreadPoolExecutor(16) as pool:
        advanced = list(pool.map(adv, [s for s in sessions for _ in (0, 1)]))
        decided = list(pool.map(dec, [s for s in sessions for _ in (0, 1)]))
    assert all(a["current_node"]["key"] == "D1" for a in advanced)
    firsts = [not d["replayed"] for d in decided]
    assert sum(firsts) == 1000 and len(decided) == 2000
    ids = [uuid.UUID(s[1]) for s in sessions]
    row = superuser.execute(
        "SELECT (SELECT count(*) FROM nukyro.session_steps WHERE session_id = ANY(%(i)s)), "
        "(SELECT count(*) FROM nukyro.session_decisions WHERE session_id = ANY(%(i)s)), "
        "(SELECT count(*) FROM nukyro.session_effects WHERE session_id = ANY(%(i)s)), "
        "(SELECT count(DISTINCT (session_id, seq)) FROM nukyro.session_steps WHERE session_id = ANY(%(i)s)), "
        "(SELECT count(*) FROM nukyro.session_variables WHERE session_id = ANY(%(i)s) "
        "AND variable_id IN (SELECT id FROM nukyro.state_variables WHERE key='p' "
        "AND version_id=%(v)s) AND value=1)",
        {"i": ids, "v": content["version"]},
    ).fetchone()
    assert row == (3000, 1000, 1000, 3000, 1000)


WRITES = [
    "insert_decision",
    "insert_decision_reason",
    "insert_effect",
    "update_variable",
    "insert_event",
    "insert_cause",
    "insert_step",
    "move_session",
]


@pytest.mark.parametrize("name", WRITES)
def test_un_fallo_en_cada_escritura_deja_cero_cambios(
    name, api_engine, superuser, content, monkeypatch
):
    secret, sid = direct_session(superuser, content)
    service.advance(api_engine, secret, sid, AdvanceIn(from_node_key="intro"))
    on_d2 = name in ("insert_event", "insert_cause")
    if on_d2:
        service.decide(
            api_engine, secret, sid, DecisionIn(node_key="D1", option_key="A", reason_keys=["R1"])
        )
    base = snapshot(superuser, sid)
    real = getattr(queries, name)
    hits = []

    def boom(*args, **kwargs):
        real(*args, **kwargs)
        hits.append(1)
        raise RuntimeError("fallo inyectado")

    monkeypatch.setattr(queries, name, boom)
    body = (
        DecisionIn(node_key="D2", option_key="D", reason_keys=[])
        if on_d2
        else DecisionIn(node_key="D1", option_key="A", reason_keys=["R1"])
    )
    with pytest.raises(RuntimeError):
        service.decide(api_engine, secret, sid, body)
    assert hits, f"{name} no se ejecutó"
    monkeypatch.undo()
    assert snapshot(superuser, sid) == base


def test_rf080_avanzar_renueva_la_actividad_del_participante(person, superuser, content):
    sid = new_session(person, content, superuser)
    owner = superuser.execute(
        "UPDATE nukyro.participants SET last_activity_at = now() - interval '40 days' "
        "WHERE id = (SELECT participant_id FROM nukyro.sessions WHERE id = %s) RETURNING id",
        (sid,),
    ).fetchone()[0]
    assert advance(person, sid, "intro").status_code == 200
    assert superuser.execute(
        "SELECT last_activity_at > now() - interval '1 day' FROM nukyro.participants WHERE id = %s",
        (owner,),
    ).fetchone() == (True,)


# --- Criterios por RF de la etapa 3 (nivel integración) ---


def values_of(db, sid):
    return dict(
        db.execute(
            "SELECT v.key, sv.value FROM nukyro.session_variables sv JOIN nukyro.state_variables v "
            "ON v.id=sv.variable_id WHERE sv.session_id=%s",
            (sid,),
        ).fetchall()
    )


def test_rf020_rf021_rf022_queda_la_alternativa_con_la_hora_del_servidor(
    person, superuser, content
):
    sid = new_session(person, content, superuser)
    advance(person, sid, "intro")
    assert decide(person, sid, "D1", "B", ["R1"]).status_code == 200
    node, option, fresh = superuser.execute(
        "SELECT n.key, o.key, d.decided_at > now() - interval '1 minute' "
        "FROM nukyro.session_decisions d JOIN nukyro.nodes n ON n.id=d.node_id "
        "JOIN nukyro.options o ON o.id=d.option_id WHERE d.session_id=%s",
        (sid,),
    ).fetchone()
    assert (node, option, fresh) == ("D1", "B", True)


def test_rf020_rf021_rf022_alternativa_de_otro_nodo_o_fecha_del_cliente_es_422(
    person, superuser, content
):
    sid = new_session(person, content, superuser)
    advance(person, sid, "intro")
    base = snapshot(superuser, sid)
    assert decide(person, sid, "D1", "C", ["R1"]).status_code == 422  # C es de D2
    for extra in ({"decided_at": "2020-01-01T00:00:00Z"}, {"id": str(uuid.uuid4())}):
        body = {"node_key": "D1", "option_key": "A", "reason_keys": ["R1"], **extra}
        r = person.post(f"/api/v1/sessions/{sid}/decisions", json=body, headers=WRITE)
        assert r.status_code == 422
    assert snapshot(superuser, sid) == base


def test_rf023_rf025_las_razones_quedan_ligadas_a_la_decision(person, superuser, content):
    sid = new_session(person, content, superuser)
    advance(person, sid, "intro")
    assert decide(person, sid, "D1", "A", ["R1", "R2"]).status_code == 200
    linked = superuser.execute(
        "SELECT r.key FROM nukyro.session_decision_reasons dr "
        "JOIN nukyro.session_decisions d ON d.id=dr.session_decision_id "
        "JOIN nukyro.justification_reasons r ON r.id=dr.reason_id "
        "WHERE d.session_id=%s ORDER BY r.key",
        (sid,),
    ).fetchall()
    assert linked == [("R1",), ("R2",)]


def test_rf023_rf025_razon_de_otro_nodo_repetida_o_no_pedida_es_422(person, superuser, content):
    sid = new_session(person, content, superuser)
    advance(person, sid, "intro")
    base = snapshot(superuser, sid)
    assert decide(person, sid, "D1", "A", ["R1", "R1"]).status_code == 422  # repetida
    assert decide(person, sid, "D1", "A", ["R1", "R9"]).status_code == 422  # inexistente
    assert snapshot(superuser, sid) == base
    assert decide(person, sid, "D1", "A", ["R1"]).status_code == 200
    base = snapshot(superuser, sid)
    assert decide(person, sid, "D2", "C", ["R1"]).status_code == 422  # R1 es de D1 y D2 no pide
    assert snapshot(superuser, sid) == base


def test_rf026_rf027_cada_sesion_parte_de_los_valores_iniciales(person, superuser, content):
    first = new_session(person, content, superuser)
    advance(person, first, "intro")
    decide(person, first, "D1", "A", ["R1"])
    second = new_session(person, content, superuser)
    assert values_of(superuser, second) == {"p": 3, "e": 3}
    assert values_of(superuser, first) == {"p": 1, "e": 3}


def test_rf026_rf027_una_sesion_no_cambia_la_de_otro_participante(
    person, new_client, superuser, content
):
    mine = new_session(person, content, superuser)
    other = new_client()
    other.post("/api/v1/participants", json=ACCEPT, headers=WRITE)
    theirs = new_session(other, content, superuser)
    before = snapshot(superuser, theirs)
    advance(person, mine, "intro")
    decide(person, mine, "D1", "B", ["R1"])
    assert snapshot(superuser, theirs) == before
    assert values_of(superuser, theirs) == {"p": 3, "e": 3}


def test_rf028_rf029_los_efectos_se_aplican_en_orden_con_limites_tras_registrar(
    person, superuser, content
):
    sid = new_session(person, content, superuser)
    advance(person, sid, "intro")
    decide(person, sid, "D1", "A", ["R1"])
    decide(person, sid, "D2", "D")
    rows = superuser.execute(
        "SELECT n.key, e.old_value, e.new_value FROM nukyro.session_effects e "
        "JOIN nukyro.session_decisions d ON d.id=e.session_decision_id "
        "JOIN nukyro.nodes n ON n.id=d.node_id WHERE e.session_id=%s ORDER BY d.decided_at",
        (sid,),
    ).fetchall()
    assert rows == [("D1", 3, 1), ("D2", 1, 0)]  # el segundo se recorta de -1 a 0
    assert values_of(superuser, sid)["p"] == 0


def test_rf028_rf029_una_peticion_invalida_deja_las_variables_iguales(person, superuser, content):
    sid = new_session(person, content, superuser)
    advance(person, sid, "intro")
    assert decide(person, sid, "D1", "A", ["R9"]).status_code == 422
    assert decide(person, sid, "D1", "A").status_code == 422
    assert values_of(superuser, sid) == {"p": 3, "e": 3}
    assert superuser.execute(
        "SELECT count(*) FROM nukyro.session_effects WHERE session_id=%s", (sid,)
    ).fetchone() == (0,)


def test_rf033_rf034_rf065_el_evento_guarda_la_regla_y_las_decisiones_causantes(
    person, superuser, content
):
    sid = new_session(person, content, superuser)
    advance(person, sid, "intro")
    decide(person, sid, "D1", "A", ["R1"])
    decide(person, sid, "D2", "D")
    rows = superuser.execute(
        "SELECT r.key, n.key FROM nukyro.session_events ev JOIN nukyro.rules r ON r.id=ev.rule_id "
        "JOIN nukyro.session_event_causes c ON c.session_event_id=ev.id "
        "JOIN nukyro.session_decisions d ON d.id=c.session_decision_id "
        "JOIN nukyro.nodes n ON n.id=d.node_id WHERE ev.session_id=%s ORDER BY 1, 2",
        (sid,),
    ).fetchall()
    assert rows == [("RULE-EV", "D1"), ("RULE-EV", "D2"), ("RULE-MALO", "D1"), ("RULE-MALO", "D2")]


def test_rf033_rf034_rf065_no_atribuye_una_rama_falsa_ni_otra_sesion(person, superuser, content):
    bad = new_session(person, content, superuser)  # A y C: evento y MALO
    good = new_session(person, content, superuser)  # B y C: sin evento
    for sid, first in ((bad, "A"), (good, "B")):
        advance(person, sid, "intro")
        decide(person, sid, "D1", first, ["R1"])
        decide(person, sid, "D2", "C")
    assert snapshot(superuser, good)[4] == 0  # session_events de la sesión sin evento
    assert superuser.execute(
        "SELECT count(*) FROM nukyro.session_event_causes c "
        "JOIN nukyro.session_decisions d ON d.id=c.session_decision_id "
        "WHERE c.session_id=%s AND d.session_id<>c.session_id",
        (bad,),
    ).fetchone() == (0,)
    # B y D: p=4 y 5; la rama falsa del any (p<=1) no se atribuye, solo D2 (chose D)
    mixed = new_session(person, content, superuser)
    advance(person, mixed, "intro")
    decide(person, mixed, "D1", "B", ["R1"])
    decide(person, mixed, "D2", "D")
    causes = superuser.execute(
        "SELECT DISTINCT n.key FROM nukyro.session_event_causes c "
        "JOIN nukyro.session_decisions d ON d.id=c.session_decision_id "
        "JOIN nukyro.nodes n ON n.id=d.node_id WHERE c.session_id=%s",
        (mixed,),
    ).fetchall()
    assert causes == [("D2",)]


def test_rf063_secreto_nodo_version_y_alternativa_validos_confirman(person, superuser, content):
    sid = new_session(person, content, superuser)
    advance(person, sid, "intro")
    r = decide(person, sid, "D1", "A", ["R1"])
    assert r.status_code == 200 and r.json()["replayed"] is False
    assert superuser.execute(
        "SELECT scenario_version_id FROM nukyro.session_decisions WHERE session_id=%s", (sid,)
    ).fetchone() == (content["version"],)


# --- Vivacidad: decidir y borrar al mismo participante (orden participante, sesión) ---


def test_decidir_y_borrar_al_participante_a_la_vez_no_se_interbloquean(
    api_engine, superuser, content
):
    def erase(participant):
        with api_engine.begin() as conn:
            return conn.execute(
                text("SELECT nukyro.erase_anonymous_participant(:p)"), {"p": participant}
            ).scalar_one()

    for _ in range(40):
        secret, sid = direct_session(superuser, content)
        participant = superuser.execute(
            "SELECT participant_id FROM nukyro.sessions WHERE id=%s", (sid,)
        ).fetchone()[0]
        service.advance(api_engine, secret, sid, AdvanceIn(from_node_key="intro"))
        barrier = threading.Barrier(2)

        def decide_now(secret=secret, sid=sid, barrier=barrier):
            barrier.wait()
            try:
                body = DecisionIn(node_key="D1", option_key="A", reason_keys=["R1"])
                return service.decide(api_engine, secret, sid, body)
            except HTTPException as exc:  # el borrado ganó la carrera: 401 o 404
                return exc.status_code

        def erase_now(participant=participant, barrier=barrier):
            barrier.wait()
            return erase(participant)

        with ThreadPoolExecutor(2) as pool:
            decided, erased = pool.submit(decide_now), pool.submit(erase_now)
            # Un interbloqueo aparecería como espera sin fin o como error de la base
            result, erased_ok = decided.result(timeout=30), erased.result(timeout=30)
        assert erased_ok is True
        assert isinstance(result, dict) or result in (401, 404)
        assert superuser.execute(
            "SELECT count(*) FROM nukyro.participants WHERE id=%s", (participant,)
        ).fetchone() == (0,)


def test_dos_alternativas_a_la_vez_dejan_una_sola_decision(api_engine, superuser, content):
    for _ in range(25):
        secret, sid = direct_session(superuser, content)
        service.advance(api_engine, secret, sid, AdvanceIn(from_node_key="intro"))
        barrier = threading.Barrier(2)

        def choose(option, secret=secret, sid=sid, barrier=barrier):
            barrier.wait()
            body = DecisionIn(node_key="D1", option_key=option, reason_keys=["R1"])
            return service.decide(api_engine, secret, sid, body)

        with ThreadPoolExecutor(2) as pool:
            first, second = pool.map(choose, ("A", "B"))
        assert first["confirmed"] == second["confirmed"]
        assert sorted([first["replayed"], second["replayed"]]) == [False, True]
        # Los efectos son solo los de la confirmada: A deja p en 1; B, en 5
        assert superuser.execute(
            "SELECT count(*) OVER (), o.key, sv.value FROM nukyro.session_decisions d "
            "JOIN nukyro.options o ON o.id = d.option_id "
            "JOIN nukyro.session_variables sv ON sv.session_id = d.session_id "
            "JOIN nukyro.state_variables v ON v.id = sv.variable_id AND v.key = 'p' "
            "WHERE d.session_id = %s",
            (sid,),
        ).fetchone() == (
            1,
            first["confirmed"]["option_key"],
            {"A": 1, "B": 5}[first["confirmed"]["option_key"]],
        )
