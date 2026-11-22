"""Entrada de la simulación: el cliente no puede enviar destinos ni fechas (RF-014, RF-015)."""

import pytest
from pydantic import ValidationError

from nukyro.modules.simulation.schemas import AdvanceIn, DecisionIn

DECISION = {"node_key": "D1", "option_key": "A", "reason_keys": ["R1"]}


def test_rf014_rf015_la_entrada_valida_solo_lleva_nodo_alternativa_y_razones():
    assert DecisionIn(**DECISION).option_key == "A"
    assert AdvanceIn(from_node_key="intro").from_node_key == "intro"


@pytest.mark.parametrize("extra", ["next_node_key", "next_node_id", "target", "decided_at"])
def test_rf014_rf015_un_destino_o_fecha_del_cliente_se_rechaza(extra):
    with pytest.raises(ValidationError):
        DecisionIn(**DECISION, **{extra: "BUENO"})
    with pytest.raises(ValidationError):
        AdvanceIn(from_node_key="intro", **{extra: "BUENO"})
