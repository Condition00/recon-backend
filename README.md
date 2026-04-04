# Recon Backend

Backend for Recon — a 3-day, 600-person DEFCON-style cybersecurity event at VIT-AP (Apr 19–21). Powers the participant PWA, admin ops dashboard, and sponsor dashboards.

## Stack

- **FastAPI** (async) — API framework
- **SQLModel** — ORM + Pydantic validation
- **PostgreSQL** via asyncpg (Neon managed)
- **Redis** — caching and pub/sub
- **Alembic** — database migrations
- **Cloudflare R2** — file storage (S3-compatible)
- **Logfire** — observability
- **uv** — package manager (not pip)

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- A running PostgreSQL instance (local or Neon)
- A running Redis instance (local or cloud)

## Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd recon-backend

# 2. Install dependencies (uv reads pyproject.toml and manages the venv automatically)
uv sync

# 3. Copy the environment file and fill in your values
cp .env.example .env
```

Edit `.env` and set at minimum:

```
MODE=development
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=recon_db
REDIS_URL=redis://localhost:6379
SECRET_KEY=<any-random-string>
GOOGLE_CLIENT_ID=<from-google-console>
GOOGLE_CLIENT_SECRET=<from-google-console>
```

## Running the server

```bash
# From the project root
uv run uvicorn app.main:app --reload --app-dir backend
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

## Database migrations

```bash
cd backend

# Create a new migration after model changes
uv run alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations
uv run alembic upgrade head

# Roll back one migration
uv run alembic downgrade -1
```

> Alembic discovers models via `app/models/__init__.py`. If you add a new domain model, import it there or it will not be picked up.

## Project structure

```
backend/app/
  core/              Config, security, OAuth — do not restructure
  db/                Async database session setup
  models/            Alembic aggregator (__init__.py imports all domain models)
  utils/             Framework plumbing — deps.py, exceptions.py, rbac.py, models/base.py
  infrastructure/    Technical capabilities — storage (R2), future: cache, realtime
  domains/           Event business logic — auth, zones, points, participants, ...
  api/v1/api.py      Mounts all routers
  main.py            App entry point — lifespan, middleware
```

See `AGENTS.md` for the full architecture guide, coding conventions, and project state.
