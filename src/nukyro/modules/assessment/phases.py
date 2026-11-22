"""Fases de la sesión derivadas de sus hitos, y abandono con fecha de corte (RF-005, RF-061)."""

from datetime import datetime


def phases(started_at, pretest_at, outcome_at, completed_at) -> list[tuple[str, datetime]]:
    """Las fases alcanzadas, en orden, con la hora de su hito."""
    steps = (
        ("started", started_at),
        ("in_scenario", pretest_at),
        ("outcome_reached", outcome_at),
        ("completed", completed_at),
    )
    return [(name, at) for name, at in steps if at is not None]


def current(started_at, pretest_at, outcome_at, completed_at) -> str:
    return phases(started_at, pretest_at, outcome_at, completed_at)[-1][0]


def is_abandoned(started_at: datetime, outcome_at: datetime | None, cutoff: datetime) -> bool:
    """Al corte, la sesión ya había empezado y aún no tenía desenlace. La fecha de corte se inyecta;
    abandonar no cierra la sesión: se puede reanudar."""
    return started_at <= cutoff and (outcome_at is None or outcome_at > cutoff)
