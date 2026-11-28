"""T-21 contra PostgreSQL y el proveedor local. Fechas históricas para aislar las pruebas."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from nukyro.db import make_engine
from nukyro.identity_provider import LocalIdentityProvider
from nukyro.retention import run_retention

from .conftest import ACCEPT, WRITE, bearer, compose, participant_id

AT = datetime(2001, 2, 28, 12, tzinfo=UTC)
TICK = timedelta(microseconds=1)
SCENARIO = {"scenario_key": "DEMO-BECAS", "self_reported_first": True}


@pytest.fixture()
def jobs_engine(settings):
    engine = make_engine(settings, "jobs")
    yield engine
    engine.dispose()


def create_account(client, token):
    return client.post("/api/v1/account/login", json={}, headers={**WRITE, **bearer(token)})


def test_t21_limites_con_dos_ejecuciones_simultaneas(
    jobs_engine, issuer_url, secrets, new_client, mint, superuser
):
    stale = new_client()
    fresh = new_client()
    for client, offset in ((stale, timedelta()), (fresh, TICK)):
        assert client.post("/api/v1/participants", json=ACCEPT, headers=WRITE).status_code == 201
        assert client.post("/api/v1/sessions", json=SCENARIO, headers=WRITE).status_code == 201
        superuser.execute(
            "UPDATE nukyro.participants SET last_activity_at = %s WHERE id = %s",
            (AT - timedelta(days=30) + offset, participant_id(superuser, client)),
        )
    active_sub = f"sub-{uuid.uuid4().hex}"
    inactive_sub = f"sub-{uuid.uuid4().hex}"
    for subject, offset in ((inactive_sub, timedelta()), (active_sub, TICK)):
        assert create_account(new_client(), mint(sub=subject)).status_code == 200
        superuser.execute(
            "UPDATE nukyro.accounts SET last_login_at = %s WHERE cognito_sub = %s",
            (datetime(2000, 2, 29, 12, tzinfo=UTC) + offset, subject),
        )
    audit_ids = [
        superuser.execute(
            "INSERT INTO nukyro.admin_audit_log (occurred_at, admin_user_id, action, entity_type) "
            "VALUES (%s, %s, 'test', 'retention') RETURNING id",
            (AT - timedelta(days=90) + offset, uuid.uuid4()),
        ).fetchone()[0]
        for offset in (timedelta(), TICK)
    ]
    provider = LocalIdentityProvider(issuer_url, secrets["NUKYRO_LOCAL_IDENTITY_ADMIN_KEY"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(run_retention, jobs_engine, provider, AT) for _ in range(2)]
        results = [future.result(timeout=15) for future in pending]
    for name in ("anonymous_expired", "accounts_blocked", "audit_logs_purged"):
        assert sum(entry[name] for entry in results) == 1
    assert sum(entry["accounts_purged"] for entry in results) == 0
    assert stale.get("/api/v1/sessions").status_code == 401
    assert fresh.get("/api/v1/sessions").status_code == 200
    assert superuser.execute(
        "SELECT status, blocked_at, deletion_due_at FROM nukyro.accounts WHERE cognito_sub = %s",
        (inactive_sub,),
    ).fetchone() == ("blocked", AT, AT + timedelta(days=30))
    assert superuser.execute(
        "SELECT status FROM nukyro.accounts WHERE cognito_sub = %s", (active_sub,)
    ).fetchone() == ("active",)
    assert superuser.execute(
        "SELECT id FROM nukyro.admin_audit_log WHERE id = ANY(%s)", (audit_ids,)
    ).fetchall() == [(audit_ids[1],)]


@pytest.mark.parametrize("already_deleted", [False, True])
def test_t21_purga_reintenta_y_el_token_emitido_durante_el_bloqueo_no_recrea(
    jobs_engine, issuer_url, secrets, new_client, mint, superuser, already_deleted
):
    subject = f"sub-{uuid.uuid4().hex}"
    client = new_client()
    assert create_account(client, mint(sub=subject)).status_code == 200
    superuser.execute(
        "SELECT nukyro.block_account_at(id, 'user_request', %s, %s) "
        "FROM nukyro.accounts WHERE cognito_sub = %s",
        (AT - timedelta(days=30), AT, subject),
    )
    late = mint(sub=subject)
    assert create_account(client, late).status_code == 403
    provider = LocalIdentityProvider(issuer_url, secrets["NUKYRO_LOCAL_IDENTITY_ADMIN_KEY"])
    assert provider.has_identity(late)
    assert run_retention(jobs_engine, provider, AT - TICK)["accounts_purged"] == 0
    wrong_key = LocalIdentityProvider(issuer_url, uuid.uuid4().hex)
    failed = run_retention(jobs_engine, wrong_key, AT)
    assert failed["identity_deletion_failed"] == 1
    assert failed["accounts_purged"] == 0
    assert provider.has_identity(late)
    assert create_account(client, late).status_code == 403

    if already_deleted:
        provider.delete_identity(subject)
    result = run_retention(jobs_engine, provider, AT)
    assert result["accounts_purged"] == 1
    assert result["identity_deletion_failed"] == 0
    assert not provider.has_identity(late)
    assert create_account(client, late).status_code == 401
    assert run_retention(jobs_engine, provider, AT)["accounts_purged"] == 0
    assert (
        superuser.execute(
            "SELECT id FROM nukyro.accounts WHERE cognito_sub = %s", (subject,)
        ).fetchone()
        is None
    )


def test_t21_compose_ejecuta_el_comando_con_instante_inyectable():
    output = compose(
        "run",
        "--build",
        "--rm",
        "--no-deps",
        "jobs",
        "python",
        "-m",
        "nukyro.cli",
        "run-retention",
        "--at",
        "1900-01-01T00:00:00Z",
    )
    assert json.loads(output.splitlines()[-1]) == {
        "anonymous_expired": 0,
        "accounts_blocked": 0,
        "accounts_purged": 0,
        "identity_deletion_failed": 0,
        "audit_logs_purged": 0,
    }
