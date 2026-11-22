"""La CLI de siembra no falla en silencio: un fallo sale con código distinto de 0 (T-13)."""

from pathlib import Path

import pytest

from nukyro import cli
from nukyro.modules.publishing.importer import SeedFailed
from nukyro.modules.publishing.service import InvalidScenario

SCENARIO = str(Path(__file__).parents[2] / "demo" / "scenario-becas.json")


class Issue:
    code, key = "no_pretest", None


@pytest.fixture
def fake_engine(monkeypatch):
    class Engine:
        disposed = False

        def dispose(self):
            Engine.disposed = True

    monkeypatch.setattr(cli, "load_admin_settings", lambda: object())
    monkeypatch.setattr(cli, "make_engine", lambda *_: Engine())
    return Engine


def test_siembra_correcta_sale_con_cero(monkeypatch, fake_engine, capsys):
    monkeypatch.setattr(cli, "seed_demo", lambda engine, spec: True)
    assert cli.main(["seed-demo", "--file", SCENARIO]) == 0
    assert "sembrado y publicado" in capsys.readouterr().out and fake_engine.disposed


def test_una_siembra_fallida_anterior_sale_distinto_de_cero_con_mensaje_claro(
    monkeypatch, fake_engine, capsys
):
    def failed(engine, spec):
        raise SeedFailed("DEMO-BECAS: queda un borrador de una siembra fallida")

    monkeypatch.setattr(cli, "seed_demo", failed)
    assert cli.main(["seed-demo", "--file", SCENARIO]) not in (0, None)
    captured = capsys.readouterr()
    assert "borrador de una siembra fallida" in captured.err and "sembrado" not in captured.out
    assert fake_engine.disposed


def test_un_escenario_que_no_valida_sale_distinto_de_cero(monkeypatch, fake_engine, capsys):
    def invalid(engine, spec):
        raise InvalidScenario([Issue()])

    monkeypatch.setattr(cli, "seed_demo", invalid)
    assert cli.main(["seed-demo", "--file", SCENARIO]) not in (0, None)
    assert "no_pretest" in capsys.readouterr().err
