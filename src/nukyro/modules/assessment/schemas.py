"""Salida de las evaluaciones: sin correctas, temas, objetivos ni aciertos por pregunta."""

from pydantic import Field, StrictStr

from nukyro.modules.entry.schemas import BaseModel, StrictInput


class AnswerIn(StrictInput):
    option_key: StrictStr = Field(min_length=1, max_length=100)


class OptionOut(BaseModel):
    key: str
    label: str


class QuestionOut(BaseModel):
    key: str
    prompt: str
    options: list[OptionOut]
    selected_option_key: str | None


class AssessmentOut(BaseModel):
    type: str
    submitted: bool
    answered: int
    total: int
    score: float | None  # porcentaje de esta evaluación, solo al terminar todas (RF-049)
    questions: list[QuestionOut]


class ProgressOut(BaseModel):
    answered: int
    total: int
    submitted: bool
