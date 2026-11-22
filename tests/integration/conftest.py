"""Fixtures de integración. Las provee scripts/verify (o el desarrollador) con el entorno:

NUKYRO_COMPOSE_ARGS  argumentos de `docker compose` (proyecto, env-file y archivos)
NUKYRO_ENV_FILE      archivo con los secretos de ese proyecto
La base debe estar arriba y migrada, con compose.test.yaml (puerto en 127.0.0.1).
"""

import os
import shlex
import subprocess
from pathlib import Path

import psycopg
import pytest

from nukyro.config import load_settings

DBNAME = "nukyro"


def compose(*args: str, env: dict[str, str] | None = None) -> str:
    cmd = ["docker", "compose", *shlex.split(os.environ["NUKYRO_COMPOSE_ARGS"]), *args]
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True, env={**os.environ, **(env or {})}
    )
    return result.stdout


@pytest.fixture(scope="session")
def secrets() -> dict[str, str]:
    lines = Path(os.environ["NUKYRO_ENV_FILE"]).read_text().splitlines()
    return dict(ln.split("=", 1) for ln in lines if "=" in ln)


@pytest.fixture(scope="session")
def host_port() -> int:
    return int(compose("port", "db", "5432").strip().rsplit(":", 1)[1])


@pytest.fixture(scope="session")
def settings(secrets, host_port):
    """Configuración de la API apuntando a la base publicada en el anfitrión."""
    env = {
        "NUKYRO_DB_HOST": "127.0.0.1",
        "NUKYRO_DB_PORT": str(host_port),
        "NUKYRO_DB_NAME": DBNAME,
    }
    for role in ("api", "admin", "jobs", "analytics"):
        env[f"NUKYRO_DB_{role.upper()}_USER"] = f"nukyro_{role}_app"
        env[f"NUKYRO_DB_{role.upper()}_PASSWORD"] = secrets[f"NUKYRO_DB_{role.upper()}_PASSWORD"]
    return load_settings(env)


def connect(settings, user: str, password: str, dbname: str = DBNAME) -> psycopg.Connection:
    return psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=dbname,
        user=user,
        password=password,
        autocommit=True,
    )


@pytest.fixture(scope="session")
def superuser(settings, secrets):
    with connect(settings, "postgres", secrets["NUKYRO_DB_SUPERUSER_PASSWORD"]) as conn:
        yield conn


@pytest.fixture(scope="session")
def owner_password(secrets) -> str:
    return secrets["NUKYRO_DB_OWNER_PASSWORD"]
