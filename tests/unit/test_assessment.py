"""Reglas puras de las evaluaciones (RF-005, RF-011, RF-050 a RF-058, RF-061, RF-056)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from nukyro.modules.assessment import phases, scoring

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("correct", "answered", "expected"),
    [
        (0, 6, "0.00"),
        (5, 6, "83.33"),  # 83.333...
        (1, 6, "16.67"),  # 16.666...: redondea hacia arriba
        (2, 3, "66.67"),
        (1, 8, "12.50"),
        (1, 16, "6.25"),
        (1, 200, "0.50"),
        (1, 3000, "0.03"),  # 0.0333...
        (6, 6, "100.00"),
        (3, 3, "100.00"),
    ],
)
def test_rf011_el_porcentaje_es_sobre_las_respondidas_con_dos_decimales(
    correct, answered, expected
):
    assert scoring.percent(correct, answered) == Decimal(expected)


def test_rf011_cero_respondidas_no_puntua():
    assert scoring.percent(0, 0) is None


def test_el_medio_punto_se_redondea_hacia_arriba():
    assert scoring.percent(1, 800) == Decimal("0.13")  # 0.125 exacto: no se redondea al par
    assert scoring.percent(3, 800) == Decimal("0.38")  # 0.375 exacto


# --- Orden de los conjuntos (RF-050, RF-052, RF-058) -----------------------------------------
ALL = {"posttest", "transfer", "causal"}


def test_el_pretest_no_depende_del_desenlace():
    assert scoring.is_turn("pretest", False, set(), set())


@pytest.mark.parametrize("kind", ["posttest", "transfer", "causal"])
def test_rf050_antes_del_desenlace_ningun_conjunto_final_es_su_turno(kind):
    assert not scoring.is_turn(kind, False, ALL, set())


def test_el_orden_es_posttest_transferencia_causal():
    assert scoring.is_turn("posttest", True, ALL, set())
    assert not scoring.is_turn("transfer", True, ALL, set())
    assert not scoring.is_turn("causal", True, ALL, {"posttest"})
    assert scoring.is_turn("transfer", True, ALL, {"posttest"})
    assert scoring.is_turn("causal", True, ALL, {"posttest", "transfer"})


def test_se_salta_un_conjunto_que_la_version_no_tiene():
    assert scoring.is_turn("causal", True, {"posttest", "causal"}, {"posttest"})
    assert scoring.is_turn("transfer", True, {"transfer", "causal"}, set())


def test_la_sesion_se_completa_con_el_ultimo_conjunto_final_enviado():
    assert not scoring.is_complete(ALL, {"posttest", "transfer"})
    assert scoring.is_complete(ALL, ALL)
    assert scoring.is_complete({"posttest"}, {"posttest", "pretest"})


def test_una_version_sin_conjuntos_finales_esta_completa_al_llegar_al_desenlace():
    assert scoring.is_complete(set(), set())


# --- Causal (RF-058) -----------------------------------------------------------------------
def test_rf058_causal_solo_si_el_nodo_esta_en_el_recorrido_o_es_destino_de_un_evento():
    assert scoring.applies(None, {"a"}, set())
    assert scoring.applies("a", {"a", "b"}, set())
    assert scoring.applies("ev", {"a"}, {"ev"})
    assert not scoring.applies("ev", {"a"}, set())
    assert not scoring.applies("out", {"a"}, {"ev"})


# --- Diferencia pre/post (RF-056) -----------------------------------------------------------
def test_rf056_diferencia_en_puntos_solo_si_hay_pre_y_post():
    assert scoring.difference(Decimal("50.00"), Decimal("83.33")) == Decimal("33.33")
    assert scoring.difference(Decimal("80.00"), Decimal("60.00")) == Decimal("-20.00")
    assert scoring.difference(None, Decimal("60.00")) is None
    assert scoring.difference(Decimal("60.00"), None) is None


# --- Fases y abandono (RF-005, RF-061) -------------------------------------------------------
def test_rf005_cuatro_fases_derivadas_de_los_hitos_con_su_hora():
    p, o, c = T0 + timedelta(minutes=1), T0 + timedelta(minutes=9), T0 + timedelta(minutes=15)
    assert phases.phases(T0, None, None, None) == [("started", T0)]
    assert phases.phases(T0, p, None, None) == [("started", T0), ("in_scenario", p)]
    assert phases.phases(T0, p, o, None)[-1] == ("outcome_reached", o)
    full = phases.phases(T0, p, o, c)
    assert [name for name, _ in full] == ["started", "in_scenario", "outcome_reached", "completed"]
    assert full[3][1] == c
    assert phases.current(T0, p, o, c) == "completed"
    assert phases.current(T0, p, o, None) == "outcome_reached"
    assert phases.current(T0, None, None, None) == "started"


CUT = T0 + timedelta(days=30)


def test_rf061_sin_desenlace_al_corte_hay_abandono():
    assert phases.is_abandoned(T0, None, CUT)
    assert phases.is_abandoned(T0, CUT + timedelta(seconds=1), CUT)  # el desenlace llegó tarde


def test_rf061_con_desenlace_no_hay_abandono():
    assert not phases.is_abandoned(T0, T0 + timedelta(days=1), CUT)
    assert not phases.is_abandoned(T0, CUT, CUT)


def test_rf061_una_sesion_posterior_al_corte_no_cuenta():
    assert not phases.is_abandoned(CUT + timedelta(seconds=1), None, CUT)


def test_rf061_la_fecha_de_corte_es_un_dato_de_entrada():
    assert not phases.is_abandoned(T0, None, T0 - timedelta(days=1))
    assert phases.is_abandoned(T0, None, T0 + timedelta(days=1))
