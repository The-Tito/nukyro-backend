"""SQL explícito de la cuenta. Cada función recibe la conexión de una transacción."""

from sqlalchemy import Connection, text


def insert_account(
    conn: Connection, sub: str, email: str, nickname: str, news: bool, surveys: bool
):
    """Crea la cuenta; None si ya existe (o la creó otra petición a la vez)."""
    return conn.execute(
        text(
            "INSERT INTO nukyro.accounts (cognito_sub, email, nickname, newsletter_opt_in, "
            "surveys_opt_in) VALUES (:s, :e, :n, :a, :b) "
            "ON CONFLICT (cognito_sub) DO NOTHING RETURNING id"
        ),
        {"s": sub, "e": email, "n": nickname, "a": news, "b": surveys},
    ).scalar_one_or_none()


def lock_account(conn: Connection, sub: str):
    """Primer bloqueo de la operación: la cuenta. Devuelve (id, status) o None."""
    return (
        conn.execute(
            text("SELECT id, status FROM nukyro.accounts WHERE cognito_sub = :s FOR UPDATE"),
            {"s": sub},
        )
        .mappings()
        .one_or_none()
    )


def refresh_account(conn: Connection, account, email: str, nickname: str) -> None:
    """Cognito manda en el correo y el nickname: se copian en cada inicio de sesión."""
    conn.execute(
        text(
            "UPDATE nukyro.accounts SET email = :e, nickname = :n, last_login_at = now() "
            "WHERE id = :a"
        ),
        {"a": account, "e": email, "n": nickname},
    )


def insert_registration_consents(conn: Connection, account, news: bool, surveys: bool) -> None:
    conn.execute(
        text(
            "INSERT INTO nukyro.consent_events (account_id, consent_type, granted, source) "
            "VALUES (:a, 'newsletter', :n, 'registration'), (:a, 'surveys', :s, 'registration')"
        ),
        {"a": account, "n": news, "s": surveys},
    )


def link_participant(conn: Connection, account, secret_hash: bytes | None) -> str:
    return conn.execute(
        text("SELECT nukyro.link_participant(:a, :h)"), {"a": account, "h": secret_hash}
    ).scalar_one()


def has_participant(conn: Connection, account) -> bool:
    return conn.execute(
        text("SELECT EXISTS (SELECT 1 FROM nukyro.participants WHERE account_id = :a)"),
        {"a": account},
    ).scalar_one()


def account_by_sub(conn: Connection, sub: str):
    return (
        conn.execute(
            text(
                "SELECT nickname, email, newsletter_opt_in, surveys_opt_in, status "
                "FROM nukyro.accounts WHERE cognito_sub = :s"
            ),
            {"s": sub},
        )
        .mappings()
        .one_or_none()
    )
