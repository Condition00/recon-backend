# AGENTS.md

## Project Context

Recon is the backend for a 3-day, 600-person DEFCON-style cybersecurity fest (Apr 19-21, VIT-AP). It powers the participant-facing PWA, admin ops dashboard, and sponsor/partner dashboards. The backend is a FastAPI application with PostgreSQL (Neon), Redis, and Logfire observability.

**External systems (do NOT rebuild):**
- **Luma** handles registration, RSVP, and ticket scanning. Participants who pass selection are directed to sign up on our platform.
- **CTFd** (self-hosted on AWS EC2) handles the CTF competition platform.
- **KOTH** runs on local VLAN-segmented infrastructure (not cloud).
- **n8n** handles form automation (Google Forms -> webhook -> our DB).
- **Grafana/CloudWatch** handles infrastructure monitoring.
- **Telegram/WhatsApp** handles volunteer comms and escalation channels.

**What this backend DOES own:**
- Participant PWA backend: schedule, zone map, queue indicators, passport points, leaderboard, push notifications, check-in state.
- NFC Lock Hunt system: `/tap`, `/solve`, `/progress`, `/final` endpoints with team state machine and NFC token verification.
- Points/passport economy: all point mutations across zones and events.
- Zone management: capacity tracking, queue position, status (red/amber/green).
- Incident logging: webhook ingestion from n8n/Google Forms.
- Admin dashboard: aggregated ops view, overrides, role checks.
- Sponsor/partner dashboard: post-event ROI metrics, footfall, engagement data.

---

## Commit Rules

- **NEVER** add "Co-Authored-By" lines or any co-author attribution in commits. Do not mention co-authorship in any capacity.

---

## Tech Stack

- **Framework:** FastAPI (async)
- **ORM / Validation:** SQLModel (SQLAlchemy + Pydantic combined)
- **Database:** PostgreSQL via asyncpg (Neon managed, serverless)
- **Cache / Messaging:** Redis (`redis.asyncio`)
- **Observability:** Logfire (auto-instrumented for FastAPI, asyncpg, Redis)
- **Auth:** Stateless JWT access tokens (60min) + stateful refresh tokens (7 days) in httpOnly cookies. OAuth via Authlib (Google).
- **Config:** Pydantic Settings (`app/core/config.py`)
- **Migrations:** Alembic (async, autodiscovery from `app/models/__init__.py`)
- **File Storage:** Cloudflare R2 (S3-compatible) with presigned URLs

---

## Architecture

### Pattern: Router -> Controller -> Service -> CRUD

```
Router (thin HTTP layer)  ->  Controller (orchestration + parsing)  ->  Service (business logic)  ->  CRUD (DB queries)
```

- **Routers** (`router.py`): Parse HTTP request, pull dependencies via `Depends()`, return response. NO business logic. No direct DB queries.
- **Controllers** (`controller.py`): Orchestration layer. Handles any pre/post-processing, payload transformation, or multi-service coordination that doesn't belong in the HTTP layer or business logic. May call multiple services. No HTTP context (`Request`/`Response`).
- **Services** (`service.py`): Pure business logic for a single concern. No HTTP context. Receives typed data, returns domain objects or raises `HTTPException`.
- **CRUD** (`crud.py`): Raw database operations only. SELECT, INSERT, UPDATE, DELETE. No business decisions.

### Audience-Based Top-Level Structure

The codebase is split by **audience** at the top level. Each top-level folder represents a distinct stakeholder surface with its own concerns and access patterns:

| Folder | Audience | What belongs here |
|---|---|---|
| `domains/` | Participants | Participant-facing event concepts. Owns DB tables. Vertical slices — one sub-folder per feature. |
| `admin/` | Ops staff / event admins | Aggregated ops dashboard, overrides, role management. Aggregates across domains. Horizontal layers inside. |
| `partners/` | Sponsors / partners | Post-event ROI metrics, footfall, engagement data, booth management. Horizontal layers inside. |
| `infrastructure/` | (app-wide) | Technical capabilities with no audience affinity — R2 storage, Redis helpers, WebSocket/chatroom. |
| `utils/` | (app-wide) | Pure framework plumbing — `Depends()`, exception classes, SQLModel base. Flat files only. |

**The decision rule:**
- Participant-facing event feature → `domains/<feature>/`
- Ops or admin surface → `admin/`
- Sponsor or partner surface → `partners/`
- Technical capability (storage, caching, realtime) → `infrastructure/<capability>/`
- Framework glue → `utils/`

`admin/` and `partners/` use **horizontal layers** internally (a single `models/`, `schemas/`, `crud/`, `service/`, `controller/`, `router/` each) because they are each a single coherent surface — not collections of independent sub-features. Their service layer will call into domain services for data rather than owning the source of truth.

### Directory Structure

```
backend/app/
  main.py                       # Lifespan, middleware, app mounts
  core/                         # Config, security, OAuth — do not restructure
    config.py
    security.py
    oauth.py
  db/
    database.py
  models/
    __init__.py                 # Alembic aggregator — import all domain models here
  utils/                        # Framework plumbing only — flat files, no sub-packages
    deps.py                     # get_db, get_redis, get_current_user, require_roles
    exceptions.py               # Shared HTTP exception classes
    rbac.py                     # Startup role seeding and admin bootstrap
    models/
      base.py                   # Base SQLModel (id, created_at, updated_at)
  infrastructure/               # Technical capabilities with logic and endpoints
    storage/                    # Cloudflare R2 — presigned upload/read URLs
      service/                  # r2_service.py — boto3 client, URL generation
      controller/               # r2_controller.py — validation, file key logic
      router/                   # r2_router.py — GET /r2/upload-url, /r2/read-url
      schemas/                  # r2_schemas.py — PresignedUploadResponse, PresignedReadResponse
      tests/
  domains/                      # Participant-facing event features — vertical slices
    auth/                       # COMPLETE — OAuth, JWT, user CRUD
      models/                   # user.py, role.py, oauth_account.py, refresh_token.py
      schemas/                  # UserRead, UserCreate, UserUpdate, UserProfile, RoleRead
      crud/                     # All DB operations for auth models
      service/                  # auth_service.py, user_service.py, helpers.py
      controller/               # auth_controller.py, user_controller.py
      router/                   # auth_router.py (/auth/*), user_router.py (/users/*)
      tests/
    participants/               # SCAFFOLD ONLY
    zones/                      # SCAFFOLD ONLY
    points/                     # SCAFFOLD ONLY
    shop/                       # SCAFFOLD ONLY
    schedule/                   # SCAFFOLD ONLY
    announcements/              # SCAFFOLD ONLY
    teams/                      # SCAFFOLD ONLY
    incidents/                  # SCAFFOLD ONLY
    webhooks/                   # SCAFFOLD ONLY
  admin/                        # SCAFFOLD ONLY — ops dashboard (horizontal layers)
    models/
    schemas/
    crud/
    service/                    # aggregates across domain services — no owned source of truth
    controller/
    router/
    tests/
  partners/                     # SCAFFOLD ONLY — sponsor/partner dashboard (horizontal layers)
    models/
    schemas/
    crud/
    service/
    controller/
    router/
    tests/
  api/
    v1/
      api.py                    # Mounts all routers — domains + admin + partners + infrastructure
```

### Adding a Participant Domain Feature

1. Create folder under `domains/<name>/` with: `__init__.py`, `models/`, `schemas/`, `crud/`, `service/`, `controller/`, `router/`, `tests/`
2. Add model imports to `app/models/__init__.py` so Alembic discovers them
3. Add one `include_router()` line in `api/v1/api.py`
4. Write tests in `domains/<name>/tests/`
5. Update the **Project State** section in this file

### Adding to Admin or Partners

Work inside `admin/` or `partners/` horizontally. New endpoints go in `router/`, new business logic in `service/`, new DB queries in `crud/`. If a new table is needed, add the model to `models/` and import it in `app/models/__init__.py`. Do not create new sub-folders inside `admin/` or `partners/` — keep them flat.

### Adding a New Infrastructure Capability

1. Create folder under `infrastructure/<name>/` with: `service/`, `controller/`, `router/` (and `schemas/`, `tests/` as needed)
2. Add one `include_router()` line in `api/v1/api.py` if it has HTTP endpoints
3. Update the **Project State** section in this file

A contributor owns their entire folder end-to-end. Cross-cutting touches (model aggregator, router mount, AGENTS.md state) are the only shared files.

---

## Base Model

All database models inherit from `app.utils.models.base.Base` which provides:
- `id`: UUID primary key (auto-generated)
- `created_at`: timezone-aware datetime with server default
- `updated_at`: timezone-aware datetime with onupdate trigger

```python
from app.utils.models.base import Base

class Zone(Base, ZoneBase, table=True):
    __tablename__ = "zones"
    # domain-specific fields here
```

---

## Dependency Injection

Never import raw Redis or Session clients in business logic. Always use `Depends()`:

```python
from app.utils.deps import get_db, get_redis, get_current_user, require_roles

@router.get("/zones")
async def list_zones(db: AsyncSession = Depends(get_db)):
    ...

@router.post("/zones/{id}/override")
async def override_zone(user: User = Depends(require_roles("admin", "ops_chief"))):
    ...
```

### Roles

Defined in `app/domains/auth/models/role.py`. Current roles: `admin`, `participant`, `partner`. Default role assigned to all new users is `participant`. Use `require_roles()` from `app/utils/deps.py` for route-level access control. Every route must declare its required role explicitly. The `applicant` role has been removed — registration and selection are handled externally by Luma.

---

## Points Economy Rule

All point mutations MUST go through the points domain service with a named reason code. No domain writes directly to the points table.

```python
await points_service.award(db, participant_id=pid, amount=50, reason="zone.nfc_lock_hunt.complete")
await points_service.award(db, participant_id=pid, amount=10, reason="zone.forensics_sprint.flag")
```

This gives a clean audit log and the leaderboard is always derivable from a single table.

---

## Observability

Logfire is auto-instrumented in `main.py` for FastAPI, asyncpg, and Redis. Do not add verbose `logging.info()` blocks. Use `logfire.span()` for meaningful business state context only:

```python
import logfire
with logfire.span("calculating_leaderboard"):
    result = await compute_leaderboard(db)
```

---

## Security Rules

- Never log or expose participant PII (emails, tokens, passwords) in responses or logs.
- All challenge/competition endpoints must be sandbox-aware.
- Access tokens are read from `access_token` httpOnly cookie, not headers.
- Refresh tokens use SHA-256 hashing in DB with theft detection (reuse = revoke all).
- Secrets and keys live in `.env` only. Never hardcode them.

---

## Database Conventions

- Use `SQLModel` with `table=True` for DB models. Use plain `SQLModel` (no `table=True`) for Pydantic schemas.
- All async: `AsyncSession`, `async def`, `await db.exec()`.
- Session lifecycle managed by `get_db()` dependency (auto-commit on success, rollback on exception).
- Foreign keys use UUID type matching the `Base.id` field.
- Migrations via Alembic: `cd backend && alembic revision --autogenerate -m "description"` then `alembic upgrade head`.

---

## Testing (For Contributors)

Pattern: HTTP in, assert the response. No direct DB manipulation in tests.

```python
async def test_zone_checkin_succeeds(client, seed_zone, seed_participant):
    response = await client.post(f"/zones/{seed_zone.id}/checkin", json={
        "participant_id": seed_participant.id
    })
    assert response.status_code == 200
    assert response.json()["status"] == "checked_in"
```

Rules:
1. One test file per router file
2. Test the happy path first, then the most obvious failure case
3. Never assert on IDs, assert on status codes and meaningful fields
4. If setup needs more than 3 things, it needs a fixture

---

## Project State (Agent-Maintained)

Agents MUST update this section after completing any meaningful change — domain additions, structural migrations, schema changes, or architectural decisions. This is the living state of the codebase. Do not leave it stale.

### Current Architecture Status

Audience-based top-level structure is complete and stable:

- **`utils/`** — flat files only: `deps.py`, `exceptions.py`, `rbac.py`, `models/base.py`
- **`infrastructure/storage/`** — fully implemented: R2 presigned upload/read URLs via boto3. Mounts at `/api/v1/r2/`
- **`domains/auth/`** — fully implemented: Google OAuth, JWT tokens, refresh/logout, user CRUD, RBAC seeding
- **`admin/`** — scaffolded (horizontal layers: models/, schemas/, crud/, service/, controller/, router/, tests/)
- **`partners/`** — scaffolded (horizontal layers: models/, schemas/, crud/, service/, controller/, router/, tests/)
- All other participant domain folders are scaffolded (empty `__init__.py` files only)
- `app/models/__init__.py` is the Alembic aggregator — import new domain models here when added
- `api/v1/api.py` mounts all routers (domains + admin + partners + infrastructure)

### Participant Domains Status

| Domain | Status | Notes |
|---|---|---|
| auth | Complete | Google OAuth, JWT tokens, refresh/logout |
| users | Complete | CRUD, role assignment, RBAC seeding. Roles: admin/participant/partner. No applicant role. |
| participants | Not started | Profile, QR check-in, NFC token assignment |
| zones | Not started | Capacity, queue, status (red/amber/green) |
| points | Not started | Passport economy, earn/spend, leaderboard |
| schedule | Not started | Sessions, announcements, zone map data |
| incidents | Not started | Webhook ingestion from n8n/Google Forms |
| webhooks | Not started | n8n form payload ingestion |
| shop | Not started | Redemption store |
| teams | Not started | Team formation and management |
| announcements | Not started | Push/broadcast announcements |

### Admin Status

| Surface | Status | Notes |
|---|---|---|
| admin | Not started | Aggregated ops dashboard, overrides, zone controls, incident feed |

### Partners Status

| Surface | Status | Notes |
|---|---|---|
| partners | Not started | Post-event ROI metrics, footfall data, engagement stats, booth management |

### Infrastructure Status

| Capability | Status | Notes |
|---|---|---|
| storage (R2) | Complete | Presigned upload/read URLs. `infrastructure/storage/`. Mounts at `/api/v1/r2/`. |
| cache (Redis) | Not started | Redis pub/sub helpers, key management utilities |
| realtime | Not started | WebSocket chatroom — planned feature |

---

## What NOT to Do

- Do not leave the **Project State** section outdated after making changes. Update it before finishing any task.
- Do not add a flat `controllers/` file outside of its audience folder. Controllers belong inside `domains/<name>/controller/`, `admin/controller/`, `partners/controller/`, or `infrastructure/<name>/controller/`.
- Do not create sub-folders inside `admin/` or `partners/`. They are single-surface, flat-layer folders. New features within them extend the existing horizontal layers, not new vertical slices.
- Do not import raw `engine` or `Redis()` in service/business logic. Use `Depends()`.
- Do not put business logic in routers. Routers validate input and call services.
- Do not create models without adding their import to `app/models/__init__.py`.
- Do not modify `core/config.py`, `core/security.py`, or `main.py` without explicit review.
- Do not build incident tracking UI, network monitoring, chat/helpdesk, or registration flows. These are handled by external tools.
