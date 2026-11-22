"""Comandos de operación. Uso: python -m nukyro.cli seed-demo [--file RUTA]."""

import argparse
import json
import os
import sys

from nukyro.config import load_admin_settings
from nukyro.db import make_engine
from nukyro.modules.publishing.importer import seed_demo
from nukyro.modules.publishing.service import InvalidScenario

DEFAULT_SCENARIO = "/app/demo/scenario-becas.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nukyro.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed-demo", help="siembra y publica el escenario de demostración")
    seed.add_argument("--file", default=os.environ.get("NUKYRO_SCENARIO_PATH") or DEFAULT_SCENARIO)
    args = parser.parse_args(argv)

    with open(args.file, encoding="utf-8") as f:
        spec = json.load(f)
    engine = make_engine(load_admin_settings(), "admin")
    try:
        created = seed_demo(engine, spec)
    except InvalidScenario as error:
        print(f"El escenario no pasa la validación: {[(i.code, i.key) for i in error.issues]}")
        return 1
    finally:
        engine.dispose()
    print(f"{spec['key']}: {'sembrado y publicado' if created else 'ya existía, no se toca'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
