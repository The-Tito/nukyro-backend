# Imagen de la API: multi-stage, sin dependencias de desarrollo y sin root.
FROM ghcr.io/astral-sh/uv:0.11.19 AS uv

FROM python:3.12-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runtime
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin nukyro
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
COPY demo/documents.json demo/scenario-becas.json ./demo/
USER 10001
EXPOSE 8000
CMD ["uvicorn", "nukyro.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
