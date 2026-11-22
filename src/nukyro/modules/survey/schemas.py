"""Entrada y salida de la encuesta no vinculada (T-16): solo las seis escalas del esquema (A-05)."""

from pydantic import Field, StrictInt

from nukyro.modules.entry.schemas import BaseModel, StrictInput


class SurveyIn(StrictInput):
    usefulness: StrictInt = Field(ge=1, le=5)
    clarity: StrictInt | None = Field(default=None, ge=1, le=5)
    decision_impact: StrictInt | None = Field(default=None, ge=1, le=5)
    causal_understanding: StrictInt | None = Field(default=None, ge=1, le=5)
    summary_usefulness: StrictInt | None = Field(default=None, ge=1, le=5)
    would_repeat: StrictInt | None = Field(default=None, ge=1, le=5)


class QuestionOut(BaseModel):
    key: str
    prompt: str
    required: bool
    min: int
    max: int


class SurveyOut(BaseModel):
    available: bool
    note: str | None = None
    notice_url: str | None = None
    can_skip: bool | None = None
    questions: list[QuestionOut] | None = None


class SubmittedOut(BaseModel):
    submitted: bool
