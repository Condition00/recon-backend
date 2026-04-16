# Best practice: Define uv version as an argument for flexibility and reproducibility
ARG UV_VERSION=0.7.18

# ── Stage 1: Builder ──────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory — .venv will be created here at /app/.venv
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install project dependencies (not the project itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable --compile-bytecode

# Copy application source code
COPY ./backend/app /app/app/
COPY ./backend/alembic /app/alembic/
COPY ./backend/alembic.ini /app/

# Sync the project itself into the environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --compile-bytecode

# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source code from the builder stage
COPY --from=builder /app/app /app/app
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini

# Ensure the installed binaries are on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
