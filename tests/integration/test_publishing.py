# ruff: noqa: E501
"""P12 con el rol admin real (T-12, RF-066, D-28): validar y publicar en una transacción."""

import json
import threading
import time
import uuid

import psycopg
import pytest

from nukyro.db import make_engine
from nukyro.engine import validation
from nukyro.modules.publishing import queries, service
from nukyro.modules.publishing.service import InvalidScenario, publish

from .conftest import DBNAME

BIG = 2**40


@pytest.fixture(scope="module")
def admin_engine(settings):
    engine = make_engine(settings, "admin")
    yield engine
    engine.dispose()


@pytest.fixture
def admin(superuser):
    return superuser.execute(
        "INSERT INTO nukyro.admin_users (cognito_sub, email, display_name) "
        "VALUES (%s, 'admin@example.test', 'Admin de prueba') RETURNING id",
        (f"sub-{uuid.uuid4().hex}",),
    ).fetchone()[0]


def build(db, with_published=True, bare=False):
    """Escenario con v1 publicada (sin contenido) y v2 borrador válido; devuelve ids por clave."""
    key = f"T12-{uuid.uuid4().hex[:8]}"
    ex = lambda sql, *p: db.execute(sql, p)  # noqa: E731
    sc = ex(
        "INSERT INTO nukyro.scenarios (key, title) VALUES (%s,%s) RETURNING id", key, key
    ).fetchone()[0]
    old = None
    if with_published:
        old = ex(
            "INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title) VALUES (%s,1,'v1') RETURNING id",
            sc,
        ).fetchone()[0]
        ex(
            "UPDATE nukyro.scenario_versions SET status='published', published_at=now() WHERE id=%s",
            old,
        )
    v = ex(
        "INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title) VALUES (%s,2,'v2 DEMOSTRACIÓN') RETURNING id",
        sc,
    ).fetchone()[0]
    ids = {"scenario": sc, "version": v, "old": old}

    def node(k, t, nxt=None):
        ids[k] = ex(
            "INSERT INTO nukyro.nodes (version_id, key, node_type, title, body) VALUES (%s,%s,%s,%s,'x') RETURNING id",
            v,
            k,
            t,
            k,
        ).fetchone()[0]

    if bare:
        node("intro", "intro")
        node("BUENO", "outcome")
        ex(
            "UPDATE nukyro.nodes SET default_next_node_id=%s WHERE id=%s",
            ids["BUENO"],
            ids["intro"],
        )
        return ids
    ex(
        "INSERT INTO nukyro.learning_objectives (version_id, key, description) VALUES (%s,'LO','x')",
        v,
    )
    ex(
        "INSERT INTO nukyro.state_variables (version_id, key, label, initial_value, min_value, max_value) VALUES (%s,'p','P',3,0,5)",
        v,
    )
    for k, t in (
        ("intro", "intro"),
        ("D1", "decision"),
        ("D2", "decision"),
        ("EV", "event"),
        ("MALO", "outcome"),
        ("BUENO", "outcome"),
    ):
        node(k, t)
    for k, nxt in (("intro", "D1"), ("D1", "D2"), ("D2", "BUENO")):
        ex("UPDATE nukyro.nodes SET default_next_node_id=%s WHERE id=%s", ids[nxt], ids[k])
    for k, just in (("D1", True), ("D2", False)):
        ex(
            "INSERT INTO nukyro.decision_points (node_id, version_id, requires_justification, learning_objective_id, affected_parties) "
            "SELECT %s,%s,%s,id,'x' FROM nukyro.learning_objectives WHERE version_id=%s",
            ids[k],
            v,
            just,
            v,
        )
    for node_k, k, eff in (("D1", "A", -2), ("D1", "B", 3), ("D2", "C", 1)):
        ids[k] = ex(
            "INSERT INTO nukyro.options (version_id, node_id, key, label, effects) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            v,
            ids[node_k],
            k,
            k,
            json.dumps([{"variable_key": "p", "op": "add", "value": eff}]),
        ).fetchone()[0]
    for k, ok in (("R1", True), ("R2", False)):
        ex(
            "INSERT INTO nukyro.justification_reasons (version_id, node_id, key, label, is_correct) VALUES (%s,%s,%s,%s,%s)",
            v,
            ids["D1"],
            k,
            k,
            ok,
        )
    for rk, typ, cond, target in (
        ("RE", "event", {"var": "p", "op": "lt", "value": 2}, "EV"),
        (
            "RT",
            "transition",
            {"any": [{"var": "p", "op": "lte", "value": 1}, {"chose": "C"}]},
            "MALO",
        ),
    ):
        ex(
            "INSERT INTO nukyro.rules (version_id, key, rule_type, from_node_id, condition, target_node_id, relation_type) VALUES (%s,%s,%s,%s,%s,%s,'causal')",
            v,
            rk,
            typ,
            ids["D2"],
            json.dumps(cond),
            ids[target],
        )
    ids["pretest"] = ex(
        "INSERT INTO nukyro.question_sets (version_id, set_type) VALUES (%s,'pretest') RETURNING id",
        v,
    ).fetchone()[0]
    add_question(db, ids, ids["pretest"], "Q1", correct=1)
    return ids


def add_question(db, ids, set_id, key, correct):
    q = db.execute(
        "INSERT INTO nukyro.questions (version_id, question_set_id, key, prompt, topic, learning_objective_id) "
        "SELECT %s,%s,%s,'?','t',id FROM nukyro.learning_objectives WHERE version_id=%s RETURNING id",
        (ids["version"], set_id, key, ids["version"]),
    ).fetchone()[0]
    for i in range(2):
        db.execute(
            "INSERT INTO nukyro.question_options (version_id, question_id, key, label, is_correct) VALUES (%s,%s,%s,'o',%s)",
            (ids["version"], q, f"{key}-{i}", i < correct),
        )


def status(db, version):
    return db.execute(
        "SELECT status, published_by, retired_at FROM nukyro.scenario_versions WHERE id=%s",
        (version,),
    ).fetchone()


def snapshot(db, ids):
    rows = db.execute(
        "SELECT id, status, published_at, published_by, retired_at FROM nukyro.scenario_versions WHERE scenario_id=%s ORDER BY id",
        (ids["scenario"],),
    ).fetchall()
    return rows


def test_un_contenido_valido_se_publica_y_retira_la_anterior(superuser, admin_engine, admin):
    ids = build(superuser)
    publish(admin_engine, ids["version"], admin)
    assert status(superuser, ids["version"])[:2] == ("published", admin)
    old = status(superuser, ids["old"])
    assert old[0] == "retired" and old[2] is not None
    with pytest.raises(service.DomainError) as e:
        publish(admin_engine, ids["version"], admin)
    assert e.value.code == "not_draft"


def test_el_contenido_valido_no_tiene_errores_y_no_exige_version_previa(
    superuser, admin_engine, admin
):
    ids = build(superuser, with_published=False)
    publish(admin_engine, ids["version"], admin)
    assert status(superuser, ids["version"])[0] == "published"


def test_solo_publica_un_administrador_activo(superuser, admin_engine, admin):
    ids = build(superuser)
    superuser.execute("UPDATE nukyro.admin_users SET is_active=false WHERE id=%s", (admin,))
    before = snapshot(superuser, ids)
    with pytest.raises(service.DomainError) as e:
        publish(admin_engine, ids["version"], admin)
    assert e.value.code == "admin_inactive"
    with pytest.raises(service.DomainError) as e:
        publish(admin_engine, ids["version"], uuid.uuid4())
    assert e.value.code == "admin_inactive"
    assert snapshot(superuser, ids) == before


def test_una_version_inexistente_o_retirada_no_se_publica(superuser, admin_engine, admin):
    with pytest.raises(service.DomainError) as e:
        publish(admin_engine, uuid.uuid4(), admin)
    assert e.value.code == "not_found"
    ids = build(superuser)
    with pytest.raises(service.DomainError) as e:
        publish(admin_engine, ids["old"], admin)  # publicada, no borrador
    assert e.value.code == "not_draft"


# --- Cada tipo inválido representable en la base se rechaza sin cambios ---------


def _set_cond(c):
    return lambda db, ids: db.execute(
        "UPDATE nukyro.rules SET condition=%s WHERE version_id=%s AND key='RE'",
        (json.dumps(c), ids["version"]),
    )


def _set_effects(e):
    return lambda db, ids: db.execute(
        "UPDATE nukyro.options SET effects=%s WHERE id=%s", (json.dumps(e), ids["A"])
    )


def _extra_node(kind):
    def go(db, ids):
        db.execute(
            "INSERT INTO nukyro.nodes (version_id, key, node_type, title, body) VALUES (%s,'X',%s,'x','x')",
            (ids["version"], kind),
        )

    return go


def _cycle(db, ids):
    db.execute("UPDATE nukyro.options SET next_node_id=%s WHERE id=%s", (ids["D1"], ids["C"]))


def _no_exit(db, ids):
    db.execute("UPDATE nukyro.nodes SET default_next_node_id=NULL WHERE id=%s", (ids["D2"],))


def _decision_without_option(db, ids):
    db.execute(
        'UPDATE nukyro.rules SET condition=\'{"var":"p","op":"lt","value":1}\' WHERE version_id=%s AND key=\'RT\'',
        (ids["version"],),
    )
    db.execute("DELETE FROM nukyro.options WHERE id=%s", (ids["C"],))


def _decision_without_point(db, ids):
    db.execute(
        "INSERT INTO nukyro.nodes (version_id, key, node_type, title, body, default_next_node_id) VALUES (%s,'X','decision','x','x',%s)",
        (ids["version"], ids["BUENO"]),
    )


def _outcome_rule(db, ids):
    db.execute(
        "INSERT INTO nukyro.rules (version_id, key, rule_type, from_node_id, condition, target_node_id, relation_type) VALUES (%s,'RX','transition',%s,'{\"chose\":\"A\"}',%s,'causal')",
        (ids["version"], ids["MALO"], ids["BUENO"]),
    )


def _event_in_route_without_exit(db, ids):
    db.execute("UPDATE nukyro.options SET next_node_id=%s WHERE id=%s", (ids["EV"], ids["A"]))


def _event_rule_to_outcome(db, ids):
    db.execute(
        "UPDATE nukyro.rules SET target_node_id=%s WHERE version_id=%s AND key='RE'",
        (ids["MALO"], ids["version"]),
    )


def _min_correct(n):
    return lambda db, ids: db.execute(
        "UPDATE nukyro.decision_points SET min_correct_reasons=%s WHERE node_id=%s", (n, ids["D1"])
    )


def _no_set(db, ids):
    db.execute("DELETE FROM nukyro.question_sets WHERE id=%s", (ids["pretest"],))


def _no_questions(db, ids):
    db.execute("DELETE FROM nukyro.questions WHERE question_set_id=%s", (ids["pretest"],))


def _pretest_no_correct(db, ids):
    db.execute(
        "UPDATE nukyro.question_options SET is_correct=false WHERE version_id=%s", (ids["version"],)
    )


def _posttest_no_correct(db, ids):
    s = db.execute(
        "INSERT INTO nukyro.question_sets (version_id, set_type) VALUES (%s,'posttest') RETURNING id",
        (ids["version"],),
    ).fetchone()[0]
    add_question(db, ids, s, "QP", correct=0)


def _unbounded_overflow(db, ids):
    db.execute(
        "UPDATE nukyro.state_variables SET min_value=NULL, max_value=NULL WHERE version_id=%s",
        (ids["version"],),
    )
    db.execute(
        "UPDATE nukyro.options SET effects=%s WHERE id=%s",
        (json.dumps([{"variable_key": "p", "op": "add", "value": 2**31 - 1}]), ids["A"]),
    )
    db.execute(
        "UPDATE nukyro.options SET effects=%s WHERE id=%s",
        (json.dumps([{"variable_key": "p", "op": "add", "value": 5}]), ids["C"]),
    )


INVALID = {
    "route_without_outcome#event": _event_in_route_without_exit,
    "wrong_target_type#event_rule": _event_rule_to_outcome,
    "unreachable_node": _extra_node("outcome"),
    "cycle": _cycle,
    "route_without_outcome": _no_exit,
    "decision_without_option": _decision_without_option,
    "decision_without_point": _decision_without_point,
    "intro_count": _extra_node("intro"),
    "outcome_with_exits": _outcome_rule,
    "invalid_condition": _set_cond({"zzz": 1}),
    "invalid_condition#bool": _set_cond({"var": "p", "op": "eq", "value": True}),
    "unknown_variable#condition": _set_cond({"var": "zz", "op": "eq", "value": 1}),
    "unknown_option": _set_cond({"chose": "ZZ"}),
    "unknown_node": _set_cond({"visited": "ZZ"}),
    "invalid_effect": _set_effects([{"variable_key": "p", "op": "mul", "value": 1}]),
    "invalid_effect#not_list": _set_effects([3]),
    "unknown_variable": _set_effects([{"variable_key": "zz", "op": "add", "value": 1}]),
    "int_out_of_range": _set_effects([{"variable_key": "p", "op": "set", "value": BIG}]),
    "variable_overflow": _unbounded_overflow,
    "insufficient_correct_reasons": _min_correct(2),
    "invalid_min_correct": _min_correct(0),
    "pretest_missing": _no_set,
    "pretest_empty": _no_questions,
    "question_correct_count": _pretest_no_correct,
    "question_correct_count#posttest": _posttest_no_correct,
}


@pytest.mark.parametrize("name", INVALID)
def test_cada_tipo_invalido_se_rechaza_sin_cambios(superuser, admin_engine, admin, name):
    ids = build(superuser)
    INVALID[name](superuser, ids)
    before = snapshot(superuser, ids)
    with pytest.raises(InvalidScenario) as e:
        publish(admin_engine, ids["version"], admin)
    expected = name.split("#")[0]
    assert expected in {i.code for i in e.value.issues}
    assert snapshot(superuser, ids) == before
    assert status(superuser, ids["old"])[0] == "published"


def test_sin_objetivos_se_rechaza_rn10(superuser, admin_engine, admin):
    ids = build(superuser, bare=True)  # sin objetivos: no hay decisiones ni preguntas posibles
    before = snapshot(superuser, ids)
    with pytest.raises(InvalidScenario) as e:
        publish(admin_engine, ids["version"], admin)
    assert {"no_objectives", "pretest_missing"} <= {i.code for i in e.value.issues}
    assert snapshot(superuser, ids) == before


def test_el_error_lista_todos_los_problemas(superuser, admin_engine, admin):
    ids = build(superuser)
    _no_set(superuser, ids)
    _min_correct(0)(superuser, ids)
    _cycle(superuser, ids)
    with pytest.raises(InvalidScenario) as e:
        publish(admin_engine, ids["version"], admin)
    assert {"pretest_missing", "invalid_min_correct", "cycle"} <= {i.code for i in e.value.issues}


# --- Atomicidad ---------------------------------------------------------------


def test_un_fallo_en_la_segunda_escritura_revierte_la_primera(superuser, admin_engine, admin):
    ids = build(superuser)
    fn = f"nukyro.t12_fail_{uuid.uuid4().hex[:6]}"
    superuser.execute(
        f"CREATE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN "
        f"IF NEW.status = 'published' AND NEW.scenario_id = '{ids['scenario']}' THEN "
        f"RAISE EXCEPTION 'fallo forzado'; END IF; RETURN NEW; END $$"
    )
    superuser.execute(
        f"CREATE TRIGGER trg_t12_fail BEFORE UPDATE ON nukyro.scenario_versions FOR EACH ROW EXECUTE FUNCTION {fn}()"
    )
    before = snapshot(superuser, ids)
    try:
        with pytest.raises(Exception, match="fallo forzado"):
            publish(admin_engine, ids["version"], admin)
        # la retirada (primera escritura) se deshizo: la anterior sigue publicada
        assert snapshot(superuser, ids) == before
        assert status(superuser, ids["old"])[0] == "published"
    finally:
        superuser.execute("DROP TRIGGER trg_t12_fail ON nukyro.scenario_versions")
        superuser.execute(f"DROP FUNCTION {fn}()")


# --- Concurrencia ---------------------------------------------------------------


def test_dos_publicaciones_simultaneas_dejan_una_publicada(superuser, admin_engine, admin):
    ids = build(superuser)
    gate = threading.Barrier(2)
    out = []

    def run():
        gate.wait()
        try:
            publish(admin_engine, ids["version"], admin)
            out.append("ok")
        except service.DomainError as e:
            out.append(e.code)

    threads = [threading.Thread(target=run) for _ in range(2)]
    [t.start() for t in threads]
    [t.join(30) for t in threads]
    assert sorted(out) == ["not_draft", "ok"]
    n = superuser.execute(
        "SELECT count(*) FROM nukyro.scenario_versions WHERE scenario_id=%s AND status='published'",
        (ids["scenario"],),
    ).fetchone()[0]
    assert n == 1


def editor(settings, secrets, sql, params, result):
    """Edita contenido como lo hace el panel: otra conexión, su propia transacción."""
    with psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=DBNAME,
        user="postgres",
        password=secrets["NUKYRO_DB_SUPERUSER_PASSWORD"],
        autocommit=True,
    ) as conn:
        try:
            conn.execute(sql, params)
            result.append("editado")
        except psycopg.errors.CheckViolation:
            result.append("rechazado")


BAD_EFFECT = json.dumps([{"variable_key": "zz", "op": "add", "value": 1}])


def test_defecto_6_la_edicion_que_va_primero_se_valida_antes_de_publicar(
    superuser, admin_engine, admin, settings, secrets
):
    ids = build(superuser)
    tx = psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=DBNAME,
        user="postgres",
        password=secrets["NUKYRO_DB_SUPERUSER_PASSWORD"],
    )
    try:
        tx.execute(
            "UPDATE nukyro.options SET effects=%s WHERE id=%s", (BAD_EFFECT, ids["A"])
        )  # sin confirmar
        out = []

        def run():
            try:
                publish(admin_engine, ids["version"], admin)
                out.append("publicado")
            except InvalidScenario:
                out.append("invalido")

        t = threading.Thread(target=run)
        t.start()
        time.sleep(1)
        assert out == []  # espera la edición en curso
        tx.commit()
        t.join(30)
    finally:
        tx.close()
    assert out == ["invalido"]
    assert status(superuser, ids["version"])[0] == "draft"
    assert status(superuser, ids["old"])[0] == "published"


def test_defecto_6_la_publicacion_que_va_primero_rechaza_la_edicion_posterior(
    superuser, admin_engine, admin, settings, secrets, monkeypatch
):
    ids = build(superuser)
    validated, release, seen, result = threading.Event(), threading.Event(), [], []
    real = validation.validate

    def slow(rows):
        seen.append(json.loads(json.dumps(rows, default=str)))
        issues = real(rows)
        validated.set()
        release.wait(10)  # ventana entre validar y escribir
        return issues

    monkeypatch.setattr(service, "validate", slow)
    pub = threading.Thread(target=lambda: publish(admin_engine, ids["version"], admin))
    pub.start()
    assert validated.wait(10)
    ed = threading.Thread(
        target=editor,
        args=(
            settings,
            secrets,
            "UPDATE nukyro.options SET effects=%s WHERE id=%s",
            (BAD_EFFECT, ids["A"]),
            result,
        ),
    )
    ed.start()
    time.sleep(1)
    assert result == []  # la edición espera: no cambia lo ya validado
    release.set()
    pub.join(30)
    ed.join(30)
    assert result == ["rechazado"]
    assert status(superuser, ids["version"])[0] == "published"
    with admin_engine.connect() as conn:  # lo publicado es exactamente lo validado
        assert (
            json.loads(json.dumps(queries.load_rows(conn, ids["version"]), default=str)) == seen[0]
        )
