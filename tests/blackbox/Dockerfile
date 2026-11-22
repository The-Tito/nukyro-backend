# Imagen de caja negra: NO contiene src/, solo habla con la API por HTTPS.
FROM ghcr.io/astral-sh/uv:0.11.19 AS uv

FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
# Solo lo que las pruebas necesitan: pytest y httpx
RUN uv sync --frozen --no-install-project --only-group dev
COPY tests/conftest.py tests/recorridos.py tests/
COPY tests/blackbox tests/blackbox
CMD ["pytest", "tests/blackbox"]
