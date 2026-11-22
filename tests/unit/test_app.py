import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import create_engine

from nukyro.main import create_app


class Body(BaseModel):
    name: str


@pytest.fixture
def app():
    app = create_app()
    app.state.engines = {"api": create_engine("sqlite://")}

    @app.post("/prueba")
    def prueba(body: Body):
        return {}

    @app.get("/falla")
    def falla():
        raise ValueError("dato-privado-123")

    return app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def test_health_200_si_la_base_responde(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_503_si_la_base_no_responde(app, client):
    app.state.engines = {"api": create_engine("sqlite:////no/existe/nukyro.db")}
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"


def test_sin_documentacion_publica(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_404_es_json_con_la_forma_del_contrato(client):
    response = client.get("/no-existe")
    assert response.status_code == 404
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message"}


def test_422_no_devuelve_la_entrada(client):
    response = client.post("/prueba", json={"name": 5, "extra": "valor-secreto-456"})
    assert response.status_code == 422
    assert "valor-secreto-456" not in response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_500_no_devuelve_trazas_ni_mensajes(client):
    response = client.get("/falla")
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "Error interno"}}


def test_los_logs_no_llevan_cookies_cuerpos_ni_query(client, caplog):
    with caplog.at_level(logging.INFO, logger="nukyro"):
        client.post(
            "/prueba?token=query-secreto",
            json={"name": "cuerpo-secreto"},
            headers={"Cookie": "__Host-sid=cookie-secreta"},
        )
        client.get("/falla")
    assert "/prueba" in caplog.text
    for secreto in ("query-secreto", "cuerpo-secreto", "cookie-secreta", "dato-privado-123"):
        assert secreto not in caplog.text
