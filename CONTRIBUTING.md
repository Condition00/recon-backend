# Contributing to Recon Backend

## Before you start

Read `AGENTS.md` in full. It defines the architecture, coding conventions, and what you are and are not allowed to touch. This document covers the mechanical setup. AGENTS.md covers everything else.

---

## Tooling — uv, not pip

This project uses [uv](https://docs.astral.sh/uv/getting-started/installation/) as the package manager. Do not use `pip` directly. uv manages the virtual environment and lockfile for you.

### Install uv

```bash
# macOS / Linux
curl -Ls https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Common commands

| What you want to do | Command |
|---|---|
| Install all dependencies | `uv sync` |
| Add a new package | `uv add <package>` |
| Remove a package | `uv remove <package>` |
| Run any command inside the venv | `uv run <command>` |
| Run the dev server | `uv run uvicorn app.main:app --reload --app-dir backend` |
| Run Alembic | `cd backend && uv run alembic <subcommand>` |

> Never run `pip install` manually. It bypasses the lockfile and will cause dependency drift.

---

## First-time local setup

```bash
# 1. Install dependencies
uv sync

# 2. Create your .env
cp .env.example .env
# Fill in DATABASE_*, REDIS_URL, SECRET_KEY, GOOGLE_CLIENT_* at minimum

# 3. Apply database migrations
cd backend
uv run alembic upgrade head
cd ..

# 4. Start the server
uv run uvicorn app.main:app --reload --app-dir backend
```

Visit `http://localhost:8000/docs` to confirm everything is running.

---

## Where does my change go?

The top-level folder structure is split by **audience**:

| Folder | Who uses it | Internal structure |
|---|---|---|
| `domains/` | Participants | Vertical slices — one sub-folder per feature |
| `admin/` | Ops staff / event admins | Single flat horizontal layer |
| `partners/` | Sponsors / partners | Single flat horizontal layer |
| `infrastructure/` | App-wide technical capabilities | One sub-folder per capability |
| `utils/` | Framework plumbing | Flat files only |

---

## Adding a participant domain feature

A domain is a participant-facing event concept (zones, points, schedule, etc.). Each is a self-contained vertical slice under `domains/`.

```
domains/<name>/
  __init__.py
  models/
    __init__.py         # re-exports only
    <name>.py           # SQLModel table=True models
  schemas/
    __init__.py
    <name>.py           # SQLModel/Pydantic request+response shapes
  crud/
    __init__.py
    <name>.py           # raw DB queries only — no business logic
  service/
    __init__.py
    <name>_service.py   # business logic — no HTTP context
  controller/
    __init__.py
    <name>_controller.py  # orchestration — calls services, no HTTP context
  router/
    __init__.py
    <name>_router.py    # HTTP layer — Depends(), request parsing, return response
  tests/
    __init__.py
```

After creating the domain:

1. Import your models in `app/models/__init__.py` so Alembic picks them up
2. Add `include_router()` in `app/api/v1/api.py`
3. Generate and apply the migration:
   ```bash
   cd backend
   uv run alembic revision --autogenerate -m "add <name> tables"
   uv run alembic upgrade head
   ```
4. Update the **Project State** table in `AGENTS.md`

---

## Adding to admin or partners

`admin/` and `partners/` are single flat surfaces. Do not create sub-folders inside them. Extend the existing horizontal layers:

- New endpoint → `router/` (new function in the existing router file)
- New business logic → `service/` (new function in the existing service file)
- New DB query → `crud/`
- New table → `models/` + import it in `app/models/__init__.py`

---

## Adding a new infrastructure capability

Infrastructure is a technical capability with no audience affinity (file storage, Redis pub/sub, WebSocket). It lives under `infrastructure/`.

```
infrastructure/<name>/
  service/       # client setup, core logic
  controller/    # validation, orchestration
  router/        # HTTP or WebSocket endpoints (if any)
  schemas/       # request/response models (if any)
  tests/
```

Mount the router in `app/api/v1/api.py` if it has HTTP endpoints. Update `AGENTS.md`.

---

## Making a change to an existing domain

- You own your entire domain folder end-to-end
- The only files you should touch outside your domain folder are:
  - `app/models/__init__.py` — to add a new model import
  - `app/api/v1/api.py` — to mount a new router
  - `AGENTS.md` — to update Project State
- Do not touch `core/`, `utils/`, or another domain's internals without explicitly flagging it

---

## Dependency injection rules

Never import raw database sessions or Redis clients in service or business logic. Always go through `Depends()`:

```python
from app.utils.deps import get_db, get_redis, get_current_user, require_roles
from app.domains.auth.models import ROLE_ADMIN

@router.get("/zones")
async def list_zones(db: AsyncSession = Depends(get_db)):
    ...

@router.post("/zones/{id}/lock")
async def lock_zone(user: User = Depends(require_roles(ROLE_ADMIN))):
    ...
```

---

## Migrations

- Always run `alembic revision --autogenerate` after changing any model
- Always run `alembic upgrade head` before starting the server after a pull
- Never edit migration files by hand unless you know exactly what you're doing
- Alembic only picks up models that are imported in `app/models/__init__.py`

```bash
cd backend
uv run alembic revision --autogenerate -m "short description of change"
uv run alembic upgrade head
```

---

## Commit rules

- Write clear, lowercase commit messages: `add zone capacity tracking`, not `Update stuff`
- Do not add "Co-Authored-By" or any co-author attribution — see AGENTS.md
- One logical change per commit

---

## Questions

Check `AGENTS.md` first. If it's not covered there, ask in the team channel.
