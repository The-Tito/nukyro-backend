"""Esquema inicial: ejecuta el SQL congelado desde bd/schema.sql.

Alembic no genera funciones, triggers ni permisos, por eso el SQL se congela con
scripts/freeze_schema.py y no se edita a mano.

Revision ID: 0001
Revises:
"""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None

SQL = Path(__file__).resolve().parent.parent / "sql" / "0001_initial.sql"


def upgrade() -> None:
    # Directo al driver y sin parámetros: psycopg admite varias sentencias y no interpreta los
    # «%» del SQL (SQLAlchemy sí los trataría como marcadores). Misma conexión y transacción.
    op.get_bind().connection.driver_connection.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    # Solo el esquema nukyro; los roles son del clúster y no se tocan
    op.execute("DROP SCHEMA nukyro CASCADE")
