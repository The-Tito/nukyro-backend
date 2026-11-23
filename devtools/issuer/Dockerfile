# Emisor de identidad simulado (D-34). Solo para el entorno local y las pruebas: no es parte de la API.
FROM ghcr.io/astral-sh/uv:0.11.19 AS uv

FROM python:3.12-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
# Las mismas versiones fijadas del proyecto (PyJWT y cryptography); la API no se instala
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd --uid 10002 --no-create-home --shell /usr/sbin/nologin issuer
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY devtools/issuer/issuer.py ./issuer.py
USER 10002
EXPOSE 8080
CMD ["python", "issuer.py"]
