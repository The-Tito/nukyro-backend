import pytest

from nukyro.config import load_owner_settings, load_settings

BASE = {"NUKYRO_DB_HOST": "db", "NUKYRO_DB_NAME": "nukyro"}
ROLES = {
    f"NUKYRO_DB_{r}_{k}": "x"
    for r in ("API", "ADMIN", "JOBS", "ANALYTICS")
    for k in ("USER", "PASSWORD")
}


def test_carga_los_cuatro_roles():
    settings = load_settings({**BASE, **ROLES})
    assert set(settings.logins) == {"api", "admin", "jobs", "analytics"}
    assert settings.port == 5432


def test_falla_si_falta_una_variable():
    env = {**BASE, **ROLES}
    del env["NUKYRO_DB_JOBS_PASSWORD"]
    with pytest.raises(RuntimeError, match="NUKYRO_DB_JOBS_PASSWORD"):
        load_settings(env)


def test_el_owner_no_entra_en_la_configuracion_de_la_api():
    env = {**BASE, "NUKYRO_DB_OWNER_USER": "o", "NUKYRO_DB_OWNER_PASSWORD": "p"}
    assert set(load_owner_settings(env).logins) == {"owner"}
    with pytest.raises(RuntimeError):
        load_settings(env)


def test_la_representacion_no_muestra_el_secreto():
    env = {k: ("secreto-xyz" if k.endswith("PASSWORD") else "u") for k in ROLES}
    settings = load_settings({**BASE, **env})
    assert "secreto-xyz" not in repr(settings)
