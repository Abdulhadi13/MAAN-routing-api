# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS base

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY app.py config.py database.py logging_config.py models.py ./
COPY database/script/queries/match-routing-rules-geojson.sql \
    database/script/queries/match-routing-rules-geojson.sql

RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid appuser --create-home appuser \
    && chown -R appuser:appuser /app

FROM base AS development

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project
COPY --chown=appuser:appuser test_app.py ./

USER appuser

EXPOSE 8000

CMD ["fastapi", "dev", "app.py", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS production

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]

CMD ["fastapi", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
