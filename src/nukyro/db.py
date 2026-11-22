"""Un Engine síncrono por rol, cada uno con su usuario de base de datos."""

from sqlalchemy import URL, Engine, create_engine, text

from nukyro.config import Settings


def make_engine(settings: Settings, role: str) -> Engine:
    login = settings.logins[role]
    url = URL.create(
        "postgresql+psycopg",
        username=login.user,
        password=login.password,
        host=settings.host,
        port=settings.port,
        database=settings.dbname,
    )
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


def build_engines(settings: Settings) -> dict[str, Engine]:
    return {role: make_engine(settings, role) for role in settings.logins}


def verify_engines(settings: Settings, engines: dict[str, Engine]) -> None:
    """Cada conexión debe ser el usuario esperado, miembro de su rol de grupo y sin superusuario."""
    for role, engine in engines.items():
        with engine.connect() as conn:
            user, member, superuser = conn.execute(
                text(
                    "SELECT current_user, pg_has_role(current_user, :grp, 'member'), "
                    "(SELECT rolsuper FROM pg_roles WHERE rolname = current_user)"
                ),
                {"grp": f"nukyro_{role}"},
            ).one()
        if user != settings.logins[role].user or not member or superuser:
            raise RuntimeError(
                f"La conexión del rol {role} no corresponde a su usuario o a su grupo"
            )
