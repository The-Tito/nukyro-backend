"""T-19: ninguna ruta de la API queda fuera del inventario ni sin autenticación (ADR-008 §5)."""

import inspect

from acceso import ENTRADA, PROPIA, PUBLICA, RUTAS, SESION, rutas_de
from fastapi.routing import APIRoute

from nukyro.main import create_app


def api_routes(routes):
    """FastAPI agrupa cada router incluido en un objeto con `original_router`: se recorre."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "original_router"):
            yield from api_routes(route.original_router.routes)


def rutas_reales() -> dict[tuple[str, str], APIRoute]:
    found = {}
    for route in api_routes(create_app().routes):
        for method in route.methods - {"HEAD", "OPTIONS"}:
            found[(method, route.path)] = route
    return found


def test_todas_las_rutas_estan_en_el_inventario_y_el_inventario_no_tiene_sobrantes():
    real, inventario = set(rutas_reales()), set(RUTAS)
    assert not real - inventario, f"rutas sin caso de acceso ajeno: {sorted(real - inventario)}"
    assert not inventario - real, (
        f"el inventario nombra rutas que no existen: {sorted(inventario - real)}"
    )


def test_el_tipo_de_cada_ruta_coincide_con_su_forma():
    for (method, path), (tipo, _body) in RUTAS.items():
        assert (tipo == SESION) == ("{session_id}" in path), (method, path)
    assert sorted(rutas_de(PUBLICA)) == [("GET", "/api/v1/entry"), ("GET", "/api/v1/health")]
    assert rutas_de(ENTRADA) == [("POST", "/api/v1/participants")]


def test_toda_ruta_que_no_es_publica_autentica_en_su_manejador():
    """Una ruta que olvida `authenticate` o `require_identity` es accesible sin identidad.

    Se mira el código fuente del manejador: es una defensa de bajo costo, no una prueba de
    comportamiento (esa es test_aislamiento.py)."""
    reales = rutas_reales()
    for key, (tipo, _body) in RUTAS.items():
        if tipo == PUBLICA:
            continue
        source = inspect.getsource(reales[key].endpoint)
        assert "authenticate(" in source or "require_identity(" in source, key


def test_las_rutas_publicas_no_leen_credenciales():
    reales = rutas_reales()
    for key in rutas_de(PUBLICA):
        source = inspect.getsource(reales[key].endpoint)
        assert "authenticate(" not in source and "require_identity(" not in source, key


def test_las_unicas_rutas_propias_son_las_que_no_reciben_el_id_de_otra_persona():
    for _method, path in rutas_de(PROPIA):
        assert "{" not in path, path
