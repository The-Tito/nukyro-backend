"""P12: publicar una versión. Una transacción; el contenido se lee tras los bloqueos (defecto 6)."""

from sqlalchemy import Engine

from nukyro.engine.model import DomainError
from nukyro.engine.validation import Issue, validate
from nukyro.modules.publishing import queries


class InvalidScenario(DomainError):
    """El borrador incumple RF-066: `issues` lista todos los errores."""

    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("invalid_scenario")
        self.issues = issues


def publish(engine: Engine, version_id, admin_id) -> None:
    """Publica el borrador y retira la versión publicada. `engine` es el del rol admin."""
    with engine.begin() as conn:
        scenario = queries.version_scenario(conn, version_id)
        if scenario is None:
            raise DomainError("not_found")
        queries.lock_scenario(conn, scenario)  # primero el escenario, luego la versión
        if queries.lock_version(conn, version_id) != "draft":
            raise DomainError("not_draft")
        if not queries.admin_is_active(conn, admin_id):
            raise DomainError("admin_inactive")
        # Tras el bloqueo: ninguna edición puede colarse entre validar y publicar
        issues = validate(queries.load_rows(conn, version_id))
        if issues:
            raise InvalidScenario(issues)
        queries.retire_published(conn, scenario)
        queries.publish_draft(conn, version_id, admin_id)
