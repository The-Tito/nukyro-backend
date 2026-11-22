# ruff: noqa: E501
"""Siembra de DEMO-BECAS (T-13, D-17): importador + P12 con el rol admin real; idempotente."""

import json
import uuid
from pathlib import Path

import pytest

from nukyro.db import make_engine
from nukyro.engine.validation import validate
from nukyro.modules.publishing import queries
from nukyro.modules.publishing.importer import SEED_SUB, SeedFailed, seed_demo
from nukyro.modules.publishing.service import InvalidScenario

SPEC = json.loads((Path(__file__).parents[2] / "demo" / "scenario-becas.json").read_text("utf-8"))
TABLES = ("scenarios", "scenario_versions", "nodes", "options", "rules", "questions", "admin_users")


@pytest.fixture(scope="module")
def admin_engine(settings):
    engine = make_engine(settings, "admin")
    yield engine
    engine.dispose()


def counts(db) -> tuple:
    return tuple(db.execute(f"SELECT count(*) FROM nukyro.{t}").fetchone()[0] for t in TABLES)


def published(db, key):
    return db.execute(
        "SELECT v.id, v.published_by FROM nukyro.scenarios s JOIN nukyro.scenario_versions v "
        "ON v.scenario_id = s.id WHERE s.key = %s AND v.status = 'published'",
        (key,),
    ).fetchall()


def seed_admin(db):
    return db.execute(
        "SELECT id, is_active FROM nukyro.admin_users WHERE cognito_sub = %s", (SEED_SUB,)
    ).fetchall()


def test_la_demo_sembrada_por_compose_cumple_conteos_y_rf_066(superuser, admin_engine):
    ((version, by),) = published(superuser, "DEMO-BECAS")
    assert seed_admin(superuser) == [
        (by, False)
    ]  # publicó el administrador técnico y quedó inactivo
    one = lambda sql: superuser.execute(sql, (version,)).fetchone()[0]  # noqa: E731
    assert one("SELECT count(*) FROM nukyro.decision_points WHERE version_id = %s") == 8
    assert one("SELECT count(*) FROM nukyro.state_variables WHERE version_id = %s") == 3
    assert (
        one("SELECT count(*) FROM nukyro.nodes WHERE version_id = %s AND node_type = 'event'") == 2
    )
    assert (
        one("SELECT count(*) FROM nukyro.nodes WHERE version_id = %s AND node_type = 'outcome'")
        == 3
    )
    assert (
        one("SELECT count(*) FROM nukyro.rules WHERE version_id = %s AND rule_type = 'transition'")
        >= 1
    )
    assert one("SELECT count(*) FROM nukyro.question_sets WHERE version_id = %s") == 4
    assert (
        one(
            "SELECT count(*) FROM nukyro.questions WHERE version_id = %s AND requires_node_id IS NOT NULL"
        )
        >= 1
    )
    with admin_engine.connect() as conn:
        assert validate(queries.load_rows(conn, version)) == []


def test_sembrar_dos_veces_no_duplica(superuser, admin_engine):
    before = counts(superuser)
    assert seed_demo(admin_engine, SPEC) is False
    assert seed_demo(admin_engine, SPEC) is False
    assert counts(superuser) == before
    assert len(published(superuser, "DEMO-BECAS")) == 1


def test_un_escenario_nuevo_se_publica_una_vez_y_el_admin_queda_inactivo(superuser, admin_engine):
    spec = {**SPEC, "key": f"T13-{uuid.uuid4().hex[:8]}"}
    before = counts(superuser)
    assert seed_demo(admin_engine, spec) is True
    after = counts(superuser)
    assert after[0] == before[0] + 1 and after[1] == before[1] + 1  # un escenario, una versión
    ((_, by),) = published(superuser, spec["key"])
    assert seed_admin(superuser) == [(by, False)]
    assert seed_demo(admin_engine, spec) is False
    assert counts(superuser) == after


@pytest.mark.parametrize("state", ["retired", "draft"])
def test_sembrar_no_toca_lo_que_dejo_un_administrador(superuser, admin_engine, state):
    key = f"T13-{uuid.uuid4().hex[:8]}"
    scenario = superuser.execute(
        "INSERT INTO nukyro.scenarios (key, title) VALUES (%s, %s) RETURNING id", (key, key)
    ).fetchone()[0]
    version = superuser.execute(
        "INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title) "
        "VALUES (%s, 1, 'Trabajo de un administrador') RETURNING id",
        (scenario,),
    ).fetchone()[0]
    if state == "retired":
        for change in (
            "status='published', published_at=now()",
            "status='retired', retired_at=now()",
        ):
            superuser.execute(
                f"UPDATE nukyro.scenario_versions SET {change} WHERE id=%s", (version,)
            )
    assert seed_demo(admin_engine, {**SPEC, "key": key}) is False
    assert superuser.execute(
        "SELECT id, status FROM nukyro.scenario_versions WHERE scenario_id=%s", (scenario,)
    ).fetchall() == [(version, state)]


def drafts_of(db, key):
    return db.execute(
        "SELECT v.id, v.status, v.created_by FROM nukyro.scenarios s JOIN nukyro.scenario_versions v "
        "ON v.scenario_id = s.id WHERE s.key = %s ORDER BY v.version_number",
        (key,),
    ).fetchall()


def test_una_siembra_fallida_no_se_da_por_buena_en_silencio(superuser, admin_engine):
    """Publicar falla (sin pre-test, D-28) y deja el borrador de la siembra; el siguiente arranque
    no responde «ya existía»: termina con error claro, sin borrar ni publicar nada."""
    key = f"T13-{uuid.uuid4().hex[:8]}"
    broken = {**SPEC, "key": key, "question_sets": {
        k: v for k, v in SPEC["question_sets"].items() if k != "pretest"
    }}  # fmt: skip
    with pytest.raises(InvalidScenario):
        seed_demo(admin_engine, broken)
    ((version, status, created_by),) = drafts_of(superuser, key)
    assert status == "draft" and seed_admin(superuser) == [(created_by, False)]
    before = counts(superuser)
    for spec in (broken, {**SPEC, "key": key}):  # tampoco con el contenido ya corregido
        with pytest.raises(SeedFailed) as error:
            seed_demo(admin_engine, spec)
        assert key in str(error.value)
    assert drafts_of(superuser, key) == [
        (version, "draft", created_by)
    ]  # nada se borra ni se publica
    assert counts(superuser) == before and seed_admin(superuser) == [(created_by, False)]


def test_un_borrador_de_otro_administrador_no_es_una_siembra_fallida(superuser, admin_engine):
    key = f"T13-{uuid.uuid4().hex[:8]}"
    other = superuser.execute(
        "INSERT INTO nukyro.admin_users (cognito_sub, email, display_name, is_active) "
        "VALUES (%s, %s, 'Administrador de prueba', true) RETURNING id",
        (f"sub-{key}", f"{key.lower()}@example.test"),
    ).fetchone()[0]
    scenario = superuser.execute(
        "INSERT INTO nukyro.scenarios (key, title) VALUES (%s, %s) RETURNING id", (key, key)
    ).fetchone()[0]
    superuser.execute(
        "INSERT INTO nukyro.scenario_versions (scenario_id, version_number, title, created_by) "
        "VALUES (%s, 1, 'Trabajo de un administrador', %s)",
        (scenario, other),
    )
    before = drafts_of(superuser, key)
    assert seed_demo(admin_engine, {**SPEC, "key": key}) is False  # se respeta, sin error
    assert drafts_of(superuser, key) == before
