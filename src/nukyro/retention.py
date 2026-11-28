"""Operaciones idempotentes de caducidad y purga con el rol jobs (T-21, RF-080)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, text

from nukyro.identity_provider import LocalIdentityProvider, ProviderUnavailable


def run_retention(engine: Engine, provider: LocalIdentityProvider, at: datetime) -> dict[str, int]:
    if at.utcoffset() is None:
        raise ValueError("Se requiere un instante con zona horaria")
    now = at.astimezone(UTC)
    with engine.begin() as conn:
        expired = conn.execute(
            text("SELECT nukyro.expire_anonymous_participants(:cutoff)"),
            {"cutoff": now - timedelta(days=30)},
        ).scalar_one()
        inactive = (
            conn.execute(
                text(
                    "SELECT id FROM nukyro.accounts WHERE status = 'active' "
                    "AND (last_login_at AT TIME ZONE 'UTC') + interval '12 months' <= "
                    "(CAST(:now AS timestamptz) AT TIME ZONE 'UTC') ORDER BY id"
                ),
                {"now": now},
            )
            .scalars()
            .all()
        )
    blocked = 0
    for account in inactive:
        with engine.begin() as conn:
            changed = conn.execute(
                text("SELECT nukyro.block_inactive_account(:account, :now)"),
                {"account": account, "now": now},
            ).scalar_one()
            blocked += int(changed)

    with engine.begin() as conn:
        due = (
            conn.execute(
                text(
                    "SELECT id FROM nukyro.accounts WHERE status = 'blocked' "
                    "AND deletion_due_at <= :now ORDER BY id"
                ),
                {"now": now},
            )
            .scalars()
            .all()
        )
    purged = 0
    failed = 0
    for account in due:
        params = {"account": account, "now": now}
        try:
            with engine.begin() as conn:
                subject = conn.execute(
                    text("SELECT nukyro.lock_due_account_for_purge(:account, :now)"), params
                ).scalar_one()
                if subject is None:
                    continue
                provider.delete_identity(subject)
                removed = conn.execute(
                    text("SELECT nukyro.purge_due_account(:account, :now)"), params
                ).scalar_one()
                purged += int(removed)
        except ProviderUnavailable:
            failed += 1

    with engine.begin() as conn:
        audit_logs = conn.execute(
            text("DELETE FROM nukyro.admin_audit_log WHERE occurred_at <= :cutoff"),
            {"cutoff": now - timedelta(days=90)},
        ).rowcount
    return {
        "anonymous_expired": expired,
        "accounts_blocked": blocked,
        "accounts_purged": purged,
        "identity_deletion_failed": failed,
        "audit_logs_purged": audit_logs,
    }
