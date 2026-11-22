"""Esquemas del recorrido de entrada. La entrada es estricta y rechaza campos desconocidos."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AcceptanceIn(StrictInput):
    age_confirmed: StrictBool
    privacy_notice_version: StrictStr = Field(max_length=64)
    terms_version: StrictStr = Field(max_length=64)


class SessionIn(StrictInput):
    scenario_key: StrictStr = Field(min_length=1, max_length=100)
    self_reported_first: StrictBool


class ParticipantOut(BaseModel):
    status: str  # created | existing


class ScenarioOut(BaseModel):
    key: str
    title: str
    version_number: int
    introduction: str  # RF-013: la de la versión fijada en la sesión


class NodeOut(BaseModel):
    key: str
    type: str
    title: str
    body: str


class PhaseOut(BaseModel):
    phase: str
    at: datetime


class SessionOut(BaseModel):
    id: UUID
    scenario: ScenarioOut
    started_at: datetime
    is_first_session: bool
    state: str  # calculado, modelo de datos §4
    phases: list[PhaseOut]  # fases alcanzadas con la hora de su hito (RF-005)
    current_node: NodeOut


class SessionsOut(BaseModel):
    sessions: list[SessionOut]
