"""Reglas puras de las evaluaciones: puntuación, orden de los conjuntos y causales aplicables.

Sin base de datos ni HTTP. Una puntuación mide una evaluación; nunca se suman en una nota de la
persona (RF-049, RN-07).
"""

from decimal import ROUND_HALF_UP, Decimal

# Orden fijo tras el desenlace (etapa 4); la reconstrucción revela respuestas y va después
FINAL = ("posttest", "transfer", "causal")
TYPES = ("pretest", *FINAL)


def percent(correct: int, answered: int) -> Decimal | None:
    """Porcentaje sobre las respondidas, a 2 decimales (mitad arriba); sin respuestas, nada."""
    if answered == 0:
        return None
    return (Decimal(100 * correct) / Decimal(answered)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def difference(pre: Decimal | None, post: Decimal | None) -> Decimal | None:
    """Diferencia en puntos entre post-test y pre-test; si falta uno, no hay diferencia (RF-056)."""
    return None if pre is None or post is None else post - pre


def applies(requires_node, path, event_targets) -> bool:
    """Una pregunta condicionada solo aplica si su nodo está en el recorrido o es destino de un
    evento activado (RF-058). Las demás aplican siempre."""
    return requires_node is None or requires_node in path or requires_node in event_targets


def is_turn(kind: str, outcome_reached: bool, present: set[str], submitted: set[str]) -> bool:
    """¿Es el turno del conjunto? El pre-test, siempre; los finales, tras el desenlace y en orden,
    saltando los que la versión no tiene (`present`)."""
    if kind == "pretest":
        return True
    if not outcome_reached:
        return False
    for earlier in FINAL:
        if earlier == kind:
            return True
        if earlier in present and earlier not in submitted:
            return False
    return False


def is_complete(present: set[str], submitted: set[str]) -> bool:
    """Todos los conjuntos finales presentes están enviados (ninguno: completa al llegar)."""
    return all(kind in submitted for kind in FINAL if kind in present)
