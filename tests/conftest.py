"""Política compartida (D-15): una prueba omitida, xfail, xpass o cero recolectadas es un fallo.

Al final imprime `NUKYRO-CONTEO passed=N`, que scripts/verify recoge para su resumen.
"""

import pytest


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    stats = session.config.pluginmanager.get_plugin("terminalreporter").stats
    count = {
        k: len(stats.get(k, []))
        for k in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")
    }
    print(f"\nNUKYRO-CONTEO passed={count['passed']}")
    problems = [k for k in ("skipped", "xfailed", "xpassed") if count[k]]
    if problems or count["passed"] == 0:
        print(f"NUKYRO-POLITICA: no se admiten {', '.join(problems) or 'cero pruebas ejecutadas'}")
        if exitstatus in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
