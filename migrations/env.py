"""Entorno de Alembic: se conecta como owner del esquema; solo ejecuta SQL (sin autogenerar)."""

from alembic import context

from nukyro.config import load_owner_settings
from nukyro.db import make_engine

engine = make_engine(load_owner_settings(), "owner")
with engine.connect() as connection:
    # alembic_version vive en public: el esquema nukyro queda igual a bd/schema.sql
    context.configure(connection=connection, version_table_schema="public")
    with context.begin_transaction():
        context.run_migrations()
    connection.commit()
engine.dispose()
