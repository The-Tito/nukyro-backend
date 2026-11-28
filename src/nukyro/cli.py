"""Comandos de operación de Nukyro."""

import argparse
import json
import os
import sys
from datetime import UTC, datetime

from nukyro.config import load_admin_settings, load_jobs_settings
from nukyro.db import make_engine
from nukyro.identity_provider import LocalIdentityProvider
from nukyro.modules.publishing.importer import SeedFailed, seed_demo
from nukyro.modules.publishing.service import InvalidScenario
from nukyro.retention import run_retention

DEFAULT_SCENARIO = "/app/demo/scenario-becas.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nukyro.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed-demo", help="siembra y publica el escenario de demostración")
    seed.add_argument("--file", default=os.environ.get("NUKYRO_SCENARIO_PATH") or DEFAULT_SCENARIO)
    retention = sub.add_parser(
        "run-retention", help="caduca y purga los datos cuyos plazos vencieron"
    )
    retention.add_argument("--at", type=parse_instant, help="instante ISO 8601 con zona horaria")
    args = parser.parse_args(argv)
    if args.command == "run-retention":
        return retention_command(args.at or datetime.now(UTC))

    with open(args.file, encoding="utf-8") as f:
        spec = json.load(f)
    engine = make_engine(load_admin_settings(), "admin")
    try:
        created = seed_demo(engine, spec)
    except InvalidScenario as error:
        issues = [(i.code, i.key) for i in error.issues]
        print(f"El escenario no pasa la validación: {issues}", file=sys.stderr)
        return 1
    except SeedFailed as error:
        print(f"La siembra no se completó: {error}", file=sys.stderr)
        return 2
    finally:
        engine.dispose()
    print(f"{spec['key']}: {'sembrado y publicado' if created else 'ya existía, no se toca'}")
    return 0


def parse_instant(value: str) -> datetime:
    try:
        instant = datetime.fromisoformat(value)
        if instant.utcoffset() is None:
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError("usa un instante ISO 8601 con zona horaria") from None
    return instant


def retention_command(at: datetime) -> int:
    issuer_url = os.environ.get("NUKYRO_LOCAL_IDENTITY_URL")
    admin_key = os.environ.get("NUKYRO_LOCAL_IDENTITY_ADMIN_KEY")
    if not issuer_url or not admin_key:
        print("Falta la configuración del proveedor de identidad local.", file=sys.stderr)
        return 2
    engine = make_engine(load_jobs_settings(), "jobs")
    try:
        result = run_retention(engine, LocalIdentityProvider(issuer_url, admin_key), at)
    finally:
        engine.dispose()
    print(json.dumps(result, sort_keys=True))
    return 1 if result["identity_deletion_failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
