"""Salida del resumen: sin correctas, sin alternativas no elegidas, sin nota global (RF-049)."""

from datetime import date

from nukyro.modules.entry.schemas import BaseModel


class ReasonOut(BaseModel):
    key: str
    label: str


class FeedbackOut(BaseModel):
    category: str
    scope: str  # decision (general) o option (de la alternativa elegida)
    body: str


class ReferenceOut(BaseModel):
    category: str
    title: str
    source: str
    url: str | None
    section: str | None
    version_label: str | None
    is_law: bool  # solo lo legal es ley (RF-047)
    jurisdiction: str | None  # solo para lo legal
    scope_note: str | None  # lo legal se limita a su jurisdicción (RF-048)
    valid_from: date | None


class DecisionOut(BaseModel):
    node_key: str
    title: str
    option_key: str
    option_label: str
    reasons: list[ReasonOut]
    feedback: list[FeedbackOut]
    references: list[ReferenceOut]


class CauseOut(BaseModel):
    node_key: str
    title: str


class ConsequenceOut(BaseModel):
    kind: str  # event o transition
    relation_type: str  # causal o risk
    node_key: str
    title: str
    explanation: str
    causes: list[CauseOut]


class ResultOut(BaseModel):
    type: str
    score: float | None
    correct_count: int
    total: int


class JustificationsOut(BaseModel):
    correct_count: int
    total: int
    rubric_version: str | None


class SummaryOut(BaseModel):
    decisions: list[DecisionOut]
    consequences: list[ConsequenceOut]
    results: list[ResultOut]
    pretest_score: float | None
    posttest_score: float | None
    difference: float | None  # puntos entre post-test y pre-test (RF-056)
    justifications: JustificationsOut
