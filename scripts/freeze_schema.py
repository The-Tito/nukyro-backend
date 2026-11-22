"""Congela bd/schema.sql en migrations/sql/0001_initial.sql, sin BEGIN ni COMMIT.

Uso: python3 scripts/freeze_schema.py           # regenera el SQL congelado
     python3 scripts/freeze_schema.py --check   # falla si el congelado no corresponde al esquema
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "bd" / "schema.sql"
TARGET = ROOT / "migrations" / "sql" / "0001_initial.sql"
HEADER = "-- GENERADO por scripts/freeze_schema.py desde bd/schema.sql. No editar a mano.\n"


def frozen() -> str:
    lines = [
        ln
        for ln in SOURCE.read_text(encoding="utf-8").splitlines()
        if ln.strip() not in ("BEGIN;", "COMMIT;")
    ]
    return HEADER + "\n".join(lines) + "\n"


def main() -> int:
    sql = frozen()
    if "--check" in sys.argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != sql:
            print(
                "migrations/sql/0001_initial.sql no corresponde a bd/schema.sql: "
                "ejecutar scripts/freeze_schema.py"
            )
            return 1
        print("SQL congelado al día")
        return 0
    TARGET.write_text(sql, encoding="utf-8")
    print(f"Escrito {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
