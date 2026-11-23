"""Fixtures de integración. Las provee scripts/verify (o el desarrollador) con el entorno:

NUKYRO_COMPOSE_ARGS  argumentos de `docker compose` (proyecto, env-file y archivos)
NUKYRO_ENV_FILE      archivo con los secretos de ese proyecto
La base debe estar arriba y migrada, con compose.test.yaml (puerto en 127.0.0.1).
"""

import hashlib
import os
import shlex
import ssl
import subprocess
import time
import uuid
from pathlib import Path

import httpx
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


# --- API real por HTTPS (la levanta scripts/verify con `up -d proxy`) ---
ORIGIN = "https://proxy"  # el mismo valor por defecto de NUKYRO_ORIGIN en compose.yaml
WRITE = {"Origin": ORIGIN, "X-Nukyro-Request": "1"}
ACCEPT = {"age_confirmed": True, "privacy_notice_version": "DEMO-1", "terms_version": "DEMO-1"}


@pytest.fixture(scope="session")
def api_https(tmp_path_factory):
    """(URL base, archivo de la CA de Caddy) de la API ya levantada; espera a que responda."""
    port = compose("port", "proxy", "443").strip().rsplit(":", 1)[1]
    ca = tmp_path_factory.mktemp("ca") / "root.crt"
    deadline = time.monotonic() + 90
    while True:
        try:  # Caddy crea su CA al arrancar
            compose("cp", "proxy:/data/caddy/pki/authorities/local/root.crt", str(ca))
            context = ssl.create_default_context(cafile=str(ca))
            base = f"https://localhost:{port}"
            httpx.get(f"{base}/api/v1/health", verify=context, timeout=5).raise_for_status()
            return base, str(ca)
        except (subprocess.CalledProcessError, httpx.HTTPError):
            if time.monotonic() > deadline:
                raise
            time.sleep(2)


@pytest.fixture
def new_client(api_https):
    base, ca = api_https
    clients = []

    def make() -> httpx.Client:
        client = httpx.Client(
            base_url=base, verify=ssl.create_default_context(cafile=ca), timeout=15
        )
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.close()


@pytest.fixture
def person(new_client):
    """Cliente con un participante nuevo (cookie incluida)."""
    client = new_client()
    assert client.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
    return client


def secret_of(client) -> str:
    return client.cookies.get("__Host-nukyro_participant")


def participant_id(superuser, client):
    digest = hashlib.sha256(secret_of(client).encode()).digest()
    row = superuser.execute(
        "SELECT id FROM nukyro.participants WHERE secret_hash = %s", (digest,)
    ).fetchone()
    return row[0]


# --- Emisor de identidad simulado (D-34): tokens para las pruebas ---
@pytest.fixture(scope="session")
def issuer_url():
    compose("up", "-d", "--wait", "issuer")
    port = compose("port", "issuer", "8080").strip().rsplit(":", 1)[1]
    return f"http://127.0.0.1:{port}"


@pytest.fixture(scope="session")
def mint(issuer_url):
    """mint(**spec) -> token de identidad. Sin campos, uno válido de una cuenta nueva."""

    def _mint(**spec) -> str:
        spec.setdefault("sub", f"sub-{uuid.uuid4().hex}")
        spec.setdefault("email", f"{uuid.uuid4().hex[:12]}@example.test")
        response = httpx.post(f"{issuer_url}/token", json=spec, timeout=10)
        response.raise_for_status()
        return response.json()["id_token"]

    return _mint


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
