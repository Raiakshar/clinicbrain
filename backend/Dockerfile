FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
