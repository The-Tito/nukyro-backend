"""Caja negra: solo habla con la API por HTTPS y valida el certificado con la CA de Caddy."""

import os
import ssl
import time

import httpx
import pytest

BASE = os.environ["NUKYRO_BASE_URL"]
CA_FILE = os.environ["NUKYRO_CA_FILE"]


@pytest.fixture(scope="module")
def client():
    # Verificación real con la CA interna de Caddy; nunca verify=False
    context = ssl.create_default_context(cafile=CA_FILE)
    with httpx.Client(base_url=BASE, verify=context, timeout=5) as client:
        deadline = time.monotonic() + 30
        while True:  # Caddy emite el certificado al arrancar
            try:
                client.get("/api/v1/health")
                break
            except httpx.TransportError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(1)
        yield client


def test_health_por_https(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_el_certificado_no_se_acepta_sin_la_ca_de_caddy():
    # Demuestra que la verificación es real: con las CA del sistema, el handshake falla
    with pytest.raises(httpx.ConnectError):
        httpx.get(f"{BASE}/api/v1/health", timeout=5)


def test_sin_documentacion_publica(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_errores_en_json_sin_trazas(client):
    response = client.get("/api/v1/no-existe")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Solicitud no válida"}}
