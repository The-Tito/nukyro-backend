"""Cierre idempotente del informe desde los puntos de entrada de operación (D-39)."""

import json
from concurrent.futures import ThreadPoolExecutor

from .conftest import compose


def test_d39_el_informe_solo_aparece_tras_el_cierre_y_el_reintento_lo_reutiliza(
    api_https, superuser
):
    version = superuser.execute(
        "SELECT v.id FROM nukyro.scenario_versions v JOIN nukyro.scenarios s ON s.id=v.scenario_id "
        "WHERE s.key='DEMO-BECAS' AND v.status='published'"
    ).fetchone()[0]
    prefix = ("exec", "-T", "api", "python", "-m", "nukyro.cli")
    assert json.loads(compose(*prefix, "read-pilot-report")) is None

    def close_report():
        return json.loads(compose(*prefix, "close-pilot-report", "--version", str(version)))

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = [
            future.result(timeout=15)
            for future in (pool.submit(close_report), pool.submit(close_report))
        ]
    assert isinstance(first["suppressed"], bool)
    assert first == second == json.loads(compose(*prefix, "read-pilot-report"))
    assert superuser.execute("SELECT count(*) FROM nukyro.pilot_report").fetchone() == (1,)
