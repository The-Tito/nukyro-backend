import re
from pathlib import Path

import psycopg
import pytest

from nukyro.config import ROLES
from nukyro.db import build_engines, verify_engines

from .conftest import DBNAME, compose, connect

ROOT = Path(__file__).resolve().parents[2]
REF_DB = "nukyro_ref"


def test_owner_sin_superusuario_y_dueno_de_la_base(superuser):
    row = superuser.execute(
        "SELECT r.rolsuper, r.rolcreaterole, r.rolcreatedb, "
        "(SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s) "
        "FROM pg_roles r WHERE r.rolname = 'nukyro_owner'",
        (DBNAME,),
    ).fetchone()
    assert row == (False, False, False, "nukyro_owner")


def test_la_migracion_dejo_la_version_0001(secrets, settings):
    with connect(settings, "nukyro_owner", secrets["NUKYRO_DB_OWNER_PASSWORD"]) as conn:
        assert conn.execute("SELECT version_num FROM public.alembic_version").fetchall() == [
            ("0001",)
        ]


def dump(dbname: str, owner_password: str) -> str:
    out = compose(
        "exec", "-T", "-e", f"PGPASSWORD={owner_password}", "db", "pg_dump", "-h", "127.0.0.1",
        "-U", "nukyro_owner", "-d", dbname, "-n", "nukyro", "--schema-only",
    )  # fmt: skip
    # Se descartan comentarios, SET y los \restrict con token aleatorio de pg_dump
    keep = [
        ln
        for ln in out.splitlines()
        if ln.strip() and not re.match(r"--|SET |SELECT pg_catalog\.set_config|\\", ln)
    ]
    return "\n".join(keep)


def test_base_migrada_equivale_a_schema_sql(superuser, settings, owner_password):
    superuser.execute(f"DROP DATABASE IF EXISTS {REF_DB}")
    superuser.execute(f"CREATE DATABASE {REF_DB} OWNER nukyro_owner")
    try:
        # Referencia: bd/schema.sql aplicado directamente por el owner, sin superusuario
        with connect(settings, "nukyro_owner", owner_password, REF_DB) as conn:
            conn.execute((ROOT / "bd" / "schema.sql").read_text(encoding="utf-8"))
        migrated = dump(DBNAME, owner_password)
        reference = dump(REF_DB, owner_password)
    finally:
        superuser.execute(f"DROP DATABASE IF EXISTS {REF_DB}")
    assert len(migrated) > 1000, "el volcado está vacío: la comparación no probaría nada"
    assert migrated == reference


@pytest.mark.parametrize("role", ROLES)
def test_cada_conexion_con_su_rol(role, settings, secrets):
    user = f"nukyro_{role}_app"
    with connect(settings, user, secrets[f"NUKYRO_DB_{role.upper()}_PASSWORD"]) as conn:
        current, member, superuser = conn.execute(
            "SELECT current_user, pg_has_role(current_user, %s, 'member'), "
            "(SELECT rolsuper FROM pg_roles WHERE rolname = current_user)",
            (f"nukyro_{role}",),
        ).fetchone()
        assert (current, member, superuser) == (user, True, False)
        # Nadie más que el owner crea objetos en el esquema
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("CREATE TABLE nukyro.intruso (id int)")


def test_los_roles_de_grupo_no_inician_sesion(settings, secrets):
    with pytest.raises(psycopg.OperationalError):
        connect(settings, "nukyro_api", secrets["NUKYRO_DB_API_PASSWORD"])


def test_la_api_verifica_una_conexion_por_rol(settings):
    engines = build_engines(settings)
    try:
        verify_engines(settings, engines)
    finally:
        for engine in engines.values():
            engine.dispose()


def test_la_api_rechaza_credenciales_de_otro_grupo(settings):
    # api con el usuario de analítica: conecta, pero no es miembro de nukyro_api
    bad = type(settings)(
        settings.host, settings.port, settings.dbname,
        {**settings.logins, "api": settings.logins["analytics"]},
    )  # fmt: skip
    engines = build_engines(bad)
    try:
        with pytest.raises(RuntimeError, match="api"):
            verify_engines(bad, engines)
    finally:
        for engine in engines.values():
            engine.dispose()
