# Migration Log — Vertical Domain Slice Restructure

## What Changed

### Old structure (deleted)
The original codebase used a horizontal layer architecture where all files of the same type lived together regardless of feature:
```
app/
  models/       — all DB models
  schemas/      — all Pydantic schemas
  crud/         — all DB queries
  services/     — all business logic
  controllers/  — all orchestration
  api/deps.py   — shared dependencies
```

### New structure
Vertical domain slices — each feature owns all its layers in one folder:
```
app/
  shared/               — cross-domain utilities
    deps/               — FastAPI Depends() (get_db, get_redis, get_current_user, require_roles)
    rbac/               — startup role seeding and admin bootstrap
    exceptions/         — shared HTTP exception classes
    storage/            — R2/S3 client and presigned URL logic
      validators/       — file type/extension/key validation
    models/
      base.py           — SQLModel base (id, created_at, updated_at)

  domains/
    auth/               — COMPLETE
      models/           — User, Role, OAuthAccount, RefreshToken (+ role constants)
      schemas/          — UserRead, UserCreate, UserUpdate, UserProfile, RoleRead
      crud/             — all DB operations for auth models
      service/          — OAuth flow, token management, user CRUD business logic
      controller/       — orchestration between service functions
      router/           — /auth/* and /users/* HTTP routes
      tests/

    participants/       — scaffold only
    zones/              — scaffold only
    points/             — scaffold only
    shop/               — scaffold only
    schedule/           — scaffold only
    announcements/      — scaffold only
    teams/              — scaffold only
    incidents/          — scaffold only
    webhooks/           — scaffold only (no models/, no crud/)
    admin/              — scaffold only (no models/, no crud/)

  api/
    v1/
      api.py            — mounts domain routers (one include_router per domain)
      routers/
        r2.py           — infrastructure router for R2 presigned URLs

  models/
    __init__.py         — Alembic aggregator (imports all domain models for discovery)
```

### Layer pattern per domain
```
Router → Controller → Service → CRUD
```
Each layer is a package (`__init__.py`) so sub-files can be added without restructuring.

---

## Key Decisions

- **`app/models/__init__.py`** stays as the central Alembic aggregator. When a new domain adds models, import them here. `alembic/env.py` does `from app.models import *` and never needs to change.
- **`shared/`** is for cross-cutting utilities with no owned DB tables. Infrastructure routers (r2) live in `api/v1/routers/` since they are not business domains.
- **`webhooks/` and `admin/`** have no `models/` or `crud/` — they read from other domains and never own tables.
- **Applicant role removed** — registration handled by Luma externally. Default role for all new users is `participant`.
- **`form_response` and `status` columns dropped** from `users` table via migration `6b1ab85af142`.

---

## Alembic Migration Added
- `2026-04-04-05-10_6b1ab85af142` — drops `form_response` (JSONB) and `status` (VARCHAR) from `users` table. Run `alembic upgrade head` before starting the server against the production DB.

---

## Files Removed
- `app/models/base.py`, `user.py`, `role.py`, `oauth_account.py`, `refresh_token.py`
- `app/schemas/` (entire directory)
- `app/crud/` (entire directory)
- `app/services/` (entire directory)
- `app/controllers/` (entire directory)
- `app/api/deps.py`
- `app/api/v1/routers/auth.py`
- `app/api/v1/routers/users.py`

## Files Updated
- `app/core/security.py` — imports from `app.domains.auth.models`
- `app/main.py` — imports `ensure_default_roles_and_admins` from `app.shared.rbac`
- `app/api/v1/api.py` — mounts `domains/auth/router` and `api/v1/routers/r2`
- `app/api/v1/routers/r2.py` — imports from `shared/storage/validators` and `domains/auth/models`
- `AGENTS.md` — updated with new directory structure and project state
