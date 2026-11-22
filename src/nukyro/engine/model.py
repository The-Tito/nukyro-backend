"""Tipos del motor (ADR-009): contenido, estado, resultado y errores del dominio."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class DomainError(Exception):
    """Error del dominio con un `code` estable para que la capa HTTP lo traduzca."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class InvalidContent(DomainError):
    """El contenido publicado no cumple la gramática del ADR-009."""


# --- Contenido -------------------------------------------------------------


@dataclass(frozen=True)
class Variable:
    key: str
    initial: int
    min_value: int
    max_value: int


@dataclass(frozen=True)
class Effect:
    variable_key: str
    op: str  # "add" | "set"
    value: int


@dataclass(frozen=True)
class Option:
    key: str
    effects: tuple[Effect, ...] = ()
    next_node_key: str | None = None


@dataclass(frozen=True)
class Reason:
    key: str
    correct: bool


@dataclass(frozen=True)
class Node:
    key: str
    kind: str  # "intro" | "narrative" | "decision" | "event" | "outcome"
    options: tuple[Option, ...] = ()
    reasons: tuple[Reason, ...] = ()
    requires_justification: bool = False
    min_correct: int = 1
    default_next_node_key: str | None = None


@dataclass(frozen=True)
class Rule:
    key: str
    node_key: str
    kind: str  # "event" | "transition"
    priority: int
    condition: Any
    target_key: str
    relation_type: str
    explanation: str


@dataclass(frozen=True)
class Content:
    nodes: Mapping[str, Node]
    variables: Mapping[str, Variable]
    rules: tuple[Rule, ...]


# --- Estado y resultado ----------------------------------------------------


@dataclass(frozen=True)
class AppliedEffect:
    variable_key: str
    previous: int
    new: int


@dataclass(frozen=True)
class Activation:
    rule_key: str
    kind: str
    target_key: str
    causes: tuple[str, ...]  # nodos de las decisiones causantes, en orden de recorrido
    relation_type: str
    explanation: str


@dataclass(frozen=True)
class Decision:
    node_key: str
    option_key: str
    reason_keys: tuple[str, ...]
    correct: bool
    effects: tuple[AppliedEffect, ...]
    activations: tuple[Activation, ...]
    next_node_key: str | None


@dataclass(frozen=True)
class State:
    current_node_key: str
    path: tuple[str, ...]
    values: Mapping[str, int]
    decisions: tuple[Decision, ...]


@dataclass(frozen=True)
class Result:
    state: State
    effects: tuple[AppliedEffect, ...]
    activations: tuple[Activation, ...]
    next_node_key: str | None
    replayed: bool
    finished: bool
