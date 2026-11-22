"""Esquemas de la simulación. Entrada estricta; la salida solo lleva lo que ve el participante."""

from pydantic import Field, StrictStr

from nukyro.modules.entry.schemas import BaseModel, SessionOut, StrictInput

Key = Field(min_length=1, max_length=100)


class DecisionIn(StrictInput):
    node_key: StrictStr = Key
    option_key: StrictStr = Key
    reason_keys: list[StrictStr] = Field(max_length=50)


class AdvanceIn(StrictInput):
    from_node_key: StrictStr = Key


class LabeledOut(BaseModel):
    key: str
    label: str


class EventOut(BaseModel):
    title: str
    body: str


class SessionDetailOut(SessionOut):
    options: list[LabeledOut]
    reasons: list[LabeledOut]
    events: list[EventOut]


class ConfirmedOut(BaseModel):
    node_key: str
    option_key: str
    reason_keys: list[str]


class DecisionOut(BaseModel):
    replayed: bool
    confirmed: ConfirmedOut
    session: SessionDetailOut
