# Handover

This document is a direct knowledge transfer for the next agent working in this repository. It is intentionally detailed and operational. The goal is that someone new can pick this up, understand what is implemented, understand what is fragile, and avoid re-learning the same failure modes.

## 1. Repository Identity

- Repo name: `recon-backend`
- Root path: `C:\Users\Rikhil Nellimarla\Projects\recon-backend`
- Primary app: FastAPI backend under `backend/app`
- Event context: Recon is the backend for a cybersecurity fest. It powers the participant PWA, admin operations surfaces, sponsor/partner workflows, announcements, check-in state, and infrastructure helpers.

This backend does not own registration or ticket scanning. Luma handles that. CTFd is external. KOTH is external. n8n is external. Do not rebuild those flows inside this app.

## 2. High-Level Architecture

The codebase uses a strict layer split:

- Router
- Controller
- Service
- CRUD

The expected flow is:

`HTTP request -> router -> controller -> service -> CRUD -> database`

Rules that matter:

- Routers should stay thin.
- Controllers orchestrate and shape data.
- Services contain business logic.
- CRUD does raw persistence only.
- Domain logic should not go directly into routers.
- Business code should not directly import raw Redis clients or the DB engine when a dependency or service abstraction already exists.

The app is split first by audience:

- `backend/app/domains/`: participant-facing product features
- `backend/app/admin/`: admin/ops surface
- `backend/app/partners/`: sponsor/partner surface
- `backend/app/infrastructure/`: app-wide technical capabilities
- `backend/app/utils/`: framework plumbing only

The important architectural distinction is:

- `domains/` is vertical by feature
- `admin/` and `partners/` are horizontal by layer
- `infrastructure/` holds shared technical systems like storage, cache, realtime

## 3. What Is Actually Implemented Right Now

There is a difference between the intended architecture and the code that currently exists. The live codebase is partly scaffolded and partly implemented.

### Implemented enough to work

- `domains/auth`
- `domains/participants`
- `domains/announcements`
- `domains/incidents`
- `partners`
- `infrastructure/storage`
- `infrastructure/cache`
- `infrastructure/realtime` exists, but the instruction file still has stale/conflicted status text

### Present but mostly scaffolded / incomplete

- `domains/zones`
- `domains/points`
- `domains/shop`
- `domains/teams`
- `domains/webhooks`
- parts of `domains/schedule`
- `admin`

Do not assume a folder existing means the feature is usable. A lot of folders only contain `__init__.py` or partial shells.

## 4. Live Router Surface

The root API mount is in [backend/app/api/v1/api.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/api/v1/api.py).

Currently mounted:

- auth router
- incidents router
- participants router
- storage router
- partners router
- schedule router

That means any newly added feature is not live until it is explicitly mounted there.

The main app bootstrap is in [backend/app/main.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/main.py). It:

- configures Logfire
- warms the DB on startup
- seeds default roles/admins
- initializes Redis from `REDIS_URL`
- sets session middleware
- sets trusted host middleware
- sets CORS
- mounts the versioned API router

If startup fails, it is usually because one of these failed:

- bad DB URL
- bad Redis URL
- missing/invalid env vars
- trusted host mismatch in requests

## 5. Critical Domain Boundaries

### Auth and User

Auth lives in `backend/app/domains/auth`.

Key points:

- Google OAuth exists.
- JWT access tokens and refresh tokens are implemented.
- Access tokens are cookie-based.
- Refresh tokens are cookie-based and stateful.
- Roles currently used are `admin`, `participant`, `partner`.
- Default role is `participant`.

The OAuth endpoints are in [backend/app/domains/auth/router/auth_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/domains/auth/router/auth_router.py).

Important behavior:

- `GET /auth/google/login` starts OAuth
- `GET /auth/google/callback` exchanges Google token, resolves user, then redirects to `FRONTEND_REDIRECT_AFTER_LOGIN`
- callback state is stored in session middleware, so cookie continuity matters

### Participants

Participants are intentionally separate from users.

That domain decision matters and should not be collapsed casually.

The participant model is in [backend/app/domains/participants/models/participant.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/domains/participants/models/participant.py).

Current model shape:

- `display_name`
- `institution`
- `year`
- `linkedin_acc`
- `github_acc`
- `x_acc`
- `phone`
- `profile_photo_file_key`
- `talent_visible`
- `talent_contact_shareable`
- `checked_in_at`
- `checked_in_by`
- `user_id`

The important constraint is:

- every participant is a user
- not every user is a participant
- `Participant.user_id` is unique

So `Participant` is an optional one-to-one profile extension of `User`.

Current participant router is in [backend/app/domains/participants/router/participant_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/domains/participants/router/participant_router.py).

Implemented endpoints:

- `POST /participants/me`
- `GET /participants/me`
- `PATCH /participants/me`
- `PATCH /participants/me/talent-visibility`
- `GET /participants/{participant_id}`
- `GET /participants`
- `POST /participants/{participant_id}/checkin`

Behavioral intent:

- users can create and manage their own participant profile
- admins can list/filter and mark checked-in state
- authenticated users can view another participant’s profile in a restricted read-only shape
- owner detection is used to signal editable vs read-only context

QR ticketing was intentionally not implemented because Luma handles ticket scanning.
NFC persistence was intentionally deferred.

### Partners

Partners are implemented as a horizontal surface under `backend/app/partners`.

The router is in [backend/app/partners/router/partner_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/partners/router/partner_router.py).

Implemented flows:

- apply as partner
- fetch own profile
- manage incentives
- manage assets
- admin list
- admin review/approve/reject

Important business behavior:

- approval promotes partner access
- asset uploads are tied into the storage flow
- partner operations depend on role gating

### Announcements

Announcements exist and are one of the more complete participant-facing modules.

The domain includes:

- feed endpoints
- admin create/update/delete
- expiry/pinning/priority support
- realtime publishing via Redis hooks after commit

There is also realtime/push-related code under `infrastructure/realtime`, but the documentation around its status is inconsistent because `AGENTS.md` currently contains unresolved merge conflict markers.

### Incidents

Incidents are marked complete in the instruction file and have real models/router/service files. They are more mature than most other domain folders.

### Schedule

There is a schedule router and models in the repo, and it is mounted, but it should be treated as partially implemented rather than fully production-grade until verified endpoint-by-endpoint.

## 6. Storage System: Important Current State

Storage lives in `backend/app/infrastructure/storage`.

Even though the filenames still say `r2`, the storage backend has already been moved conceptually toward AWS S3.

Key files:

- [backend/app/infrastructure/storage/router/r2_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/infrastructure/storage/router/r2_router.py)
- [backend/app/infrastructure/storage/controller/r2_controller.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/infrastructure/storage/controller/r2_controller.py)
- [backend/app/infrastructure/storage/service/r2_service.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/infrastructure/storage/service/r2_service.py)
- [backend/app/infrastructure/storage/schemas/r2_schemas.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/infrastructure/storage/schemas/r2_schemas.py)

Current route prefix is still `/r2`.

Do not assume that means Cloudflare R2 is still the active target. The implementation was changed to use AWS S3-style boto3 credential resolution.

Current storage expectations:

- presigned upload URLs
- presigned read URLs
- namespace-aware authorization

Important security behavior that was added:

- read access is not just regex-based anymore
- the code authorizes based on namespace ownership and audience rules
- participant private objects are not universally readable
- partner private objects are not universally readable
- admin namespace is admin-only
- legacy `assets/{user_id}/...` is constrained to owner/admin

There is an important mismatch to understand:

- route names and filenames still say `r2`
- backend config now expects S3-style settings

This is deliberate transitional naming, not a fully renamed surface.

## 7. Cache and Realtime

`backend/app/infrastructure/cache/service` contains:

- `cache_service.py`
- `keys.py`

The cache helpers exist and are intended for:

- get/set/delete
- TTL
- sorted sets
- counters
- pub/sub-related helpers

Realtime code exists under `backend/app/infrastructure/realtime`.

Files present:

- `service/announcement_events.py`
- `service/push_notifications.py`
- `router/announcement_ws_router.py`

But the authoritative status is muddy because `AGENTS.md` has unresolved conflict markers in the infrastructure section. Another agent should resolve that documentation conflict before trusting it.

## 8. Configuration Model

Configuration is in [backend/app/core/config.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/core/config.py).

This file now matters more than before because production validation was tightened.

### Mode handling

`MODE` supports:

- `development`
- `production`
- `testing`

Default is `development`.

### App/frontend/auth URL settings

These are important:

- `APP_BASE_URL`
- `API_BASE_URL`
- `FRONTEND_REDIRECT_AFTER_LOGIN`
- `ALLOWED_ORIGINS`
- `TRUSTED_HOSTS`

OAuth-specific:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

Behavior:

- if `GOOGLE_REDIRECT_URI` is blank, it is derived from `API_BASE_URL + /api/v1/auth/google/callback`
- callback and frontend redirect are intentionally separate concerns

Difference:

- `GOOGLE_REDIRECT_URI` is where Google returns to the backend
- `FRONTEND_REDIRECT_AFTER_LOGIN` is where the backend sends the browser after login completes

### Session settings

- `SESSION_COOKIE_NAME`
- `SESSION_MAX_AGE_SECONDS`
- `SESSION_SAME_SITE`
- `SESSION_HTTPS_ONLY`

These are used in `SessionMiddleware` and matter directly for OAuth state handling.

### Database settings

Standard DB fields exist:

- `DATABASE_USER`
- `DATABASE_PASSWORD`
- `DATABASE_HOST`
- `DATABASE_PORT`
- `DATABASE_NAME`
- `ASYNC_DATABASE_URI`

Behavior:

- if `ASYNC_DATABASE_URI` is blank, it is assembled from the individual DB fields
- non-development modes add `ssl=require`

### Storage settings

Current storage config fields:

- `S3_BUCKET_NAME`
- `AWS_REGION`
- `AWS_S3_ENDPOINT_URL`

The storage client is now expected to rely on boto3 credential resolution, not explicit R2-style account credentials.

### Other envs

- `REDIS_URL`
- `LOGFIRE_TOKEN`
- `LOGFIRE_ENVIRONMENT`
- `FCM_SERVER_KEY`
- `FCM_TOPIC`
- `OPENAI_API_KEY`

`FCM` is only relevant for push notification delivery. It is not required for basic backend operation.

### Production validation

In production mode, config validation now rejects:

- missing base URLs
- empty `ALLOWED_ORIGINS`
- localhost URLs
- copied-domain leftovers like `traction-ai.me`
- `SESSION_HTTPS_ONLY=false`

This is intentional fail-fast behavior.

## 9. Environment File Conventions

There are multiple env files in the repo now:

- `.env`
- `.env.example`
- `.env.deployment`

Expected usage:

- `.env` is for local runnable development
- `.env.example` is the reference template
- `.env.deployment` is the production/deployment-shaped template

Important operational gotcha:

Docker `--env-file` does not strip quotes.

That means this is wrong in env files used by Docker:

```env
REDIS_URL="rediss://..."
```

It must be:

```env
REDIS_URL=rediss://...
```

This caused a real startup failure with `redis.from_url()` because the scheme became `"rediss://` instead of `rediss://`.

Treat scalar env values in Docker env files as unquoted unless a tool explicitly requires otherwise.

## 10. Database and Alembic

This repo uses Alembic with SQLModel metadata autodiscovery through [backend/app/models/__init__.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/models/__init__.py).

This file is critical.

If a model is not imported there, Alembic can mis-detect the schema and generate destructive junk.

That is not theoretical. It already happened here.

### Current aggregator imports

It currently imports at least:

- auth models
- incidents
- announcements
- partners
- participants
- schedule models

If a new domain table is added and not imported there, autogenerate can think the table was deleted.

### Important migration history and repair

There was a real migration layering problem caused by a bad PR migration plus a missing announcements import.

Important migrations:

- `cb0dd356e35b` for partners
- `d1f2a3b4c5d6` for announcements
- `4c208084908b` for participants
- `7551ef70cf66` schedule-related migration that originally contained bad autogenerated announcement drops and had to be repaired
- `1dff7bf50d72` repair migration for missing announcements table drift

What went wrong historically:

- `app/models/__init__.py` did not import announcements
- Alembic autogenerate interpreted that as the table being removed
- a migration was generated with `DROP TABLE announcements` and index drops
- some DB state was already drifted/stamped forward

What was done to stabilize it:

- added announcements back to the model aggregator
- removed the accidental drop logic from the schedule migration
- added a safe repair migration that creates `announcements` only if it is missing

### Current Alembic expectations

Standard commands from `backend/`:

```powershell
uv run alembic current
uv run alembic heads
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "message"
```

Workflow discipline:

1. ensure your model imports are present in `app/models/__init__.py`
2. run `alembic upgrade head`
3. run `alembic revision --autogenerate`
4. inspect the migration carefully before trusting it
5. only then apply it

Do not trust autogenerate blindly in this repo.

## 11. Testing Strategy and Current Fixture Setup

Testing in this repo is endpoint-first.

The basic rule is:

- send HTTP requests to the FastAPI app
- assert status codes and meaningful response fields

The shared backend fixtures are in [backend/tests/conftest.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/tests/conftest.py).

Important implementation details:

- tests use `sqlite+aiosqlite://`
- SQLModel metadata is created for the test DB
- `StaticPool` is used
- dependency override replaces `get_db`
- auth override replaces `get_current_user`
- seeded roles fixture inserts `admin`, `participant`, `partner`
- `create_user` is the main user-seeding helper
- tests use `httpx.AsyncClient` with `ASGITransport`

What this means in practice:

- authenticated routes are tested by dependency override, not full OAuth
- DB state is seeded with fixtures, not through external systems
- most useful tests live next to router code

Current test files worth reading:

- [backend/app/domains/auth/tests/test_auth_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/domains/auth/tests/test_auth_router.py)
- [backend/app/domains/participants/tests/test_participant_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/domains/participants/tests/test_participant_router.py)
- [backend/app/partners/tests/test_partner_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/partners/tests/test_partner_router.py)
- [backend/app/infrastructure/storage/tests/test_r2_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/infrastructure/storage/tests/test_r2_router.py)

Typical commands:

```powershell
uv run pytest
uv run pytest backend/app/domains/participants/tests
uv run pytest backend/app/partners/tests -q
uv run pytest -k participant -vv
```

## 12. Authentication and OAuth Gotchas

The OAuth flow relies on `SessionMiddleware`.

That means:

- `/auth/google/login` stores state in the session cookie
- `/auth/google/callback` expects the same session cookie back

Things that break it:

- login on one backend origin and callback on another
- cookie not sent back on callback
- duplicated login starts overwriting state
- mismatched trusted hosts

If you see `MismatchingStateError`, think cookie/session continuity first, not “Google cannot reach the container”.

Also note:

- trusted hosts are enforced now
- CORS is explicit
- callback redirect no longer points to `/test.html`

## 13. Startup and Runtime Dependencies

The app expects the following to be viable at startup:

- database
- Redis
- valid settings

Startup path in `main.py` does:

1. `SELECT 1` against the DB
2. role/admin seeding
3. `redis.from_url(settings.REDIS_URL, decode_responses=True)`

If Redis URL is malformed, the app fails before serving requests.

If the DB is unreachable, the app fails before serving requests.

This is good behavior for deployment, but it means local runs need correct envs.

## 14. Notable Operational Footguns

These are the real things that have already caused breakage.

### 1. `AGENTS.md` currently contains merge conflict markers

There is an unresolved block in the infrastructure status section:

- `<<<<<<< feature/cache-domain`
- `=======`
- `>>>>>>> main`

That file is supposed to be the repo’s live state contract. Right now it is partially untrustworthy until that conflict is resolved.

### 2. Route/file naming still says `r2`

The storage code uses S3-style configuration, but filenames and route prefixes still say `r2`.

This can confuse new contributors. It is a naming debt, not necessarily a runtime bug.

### 3. Alembic can generate destructive migrations if the model aggregator is incomplete

Always inspect `backend/app/models/__init__.py` before autogenerate if you are adding tables.

### 4. Docker env files should not quote scalar values

Quoted `REDIS_URL` already caused a real deployment startup failure.

### 5. OAuth state errors are usually session/cookie continuity issues

Do not immediately blame Docker networking or Google reachability.

### 6. Production config is now stricter than before

Old copied-domain or localhost habits that previously “sort of worked” will now fail validation in production mode.

## 15. Current Design Decisions That Should Be Preserved Unless Intentionally Changed

These were deliberate and should not be undone casually.

### Participants stay separate from users

Do not move participant-only fields into `User` unless the domain model itself changes.

### QR endpoint was intentionally omitted

Luma handles ticket scanning. Building local QR ticketing right now would duplicate an external system.

### NFC low-level persistence was deferred

If NFC needs to be surfaced later, it should probably derive from participant identity or a narrow domain-specific token story, not an overbuilt early subsystem.

### Storage auth is namespace-based

Do not revert back to “if the key matches a regex, mint the read URL”.

### Auth redirect URLs are config-driven

Do not reintroduce hardcoded callback or frontend redirect URLs.

## 16. Practical Workflow for the Next Agent

If you are asked to add a new domain feature:

1. create the domain slice under `backend/app/domains/<feature>/`
2. implement model/schema/crud/service/controller/router
3. add model import to `backend/app/models/__init__.py`
4. mount the router in `backend/app/api/v1/api.py`
5. write endpoint tests
6. run pytest
7. if schema changed, autogenerate Alembic and inspect it
8. update `AGENTS.md`

If you are asked to add to partners:

1. stay inside the flat `partners/` structure
2. do not create sub-feature folders
3. write router tests for permission and behavior

If you are asked to change auth or app boot:

1. read `config.py`
2. read `main.py`
3. check tests in `domains/auth/tests`
4. be aware that these changes can break startup, cookies, and local test initialization very quickly

If you are asked to touch migrations:

1. inspect current heads
2. inspect model aggregator imports
3. autogenerate only after the models are correctly imported
4. inspect for accidental drops

## 17. Recommended Immediate Cleanup Items

These are not all urgent product features, but they would reduce future breakage.

1. Resolve the merge conflict markers in `AGENTS.md`.
2. Decide whether storage routes/files should be renamed from `r2` to `s3` for clarity.
3. Verify the mounted `schedule` router is actually production-ready, since it is mounted but still conceptually partial.
4. Audit `domains/incidents` against the stated “complete” status and confirm tests exist.
5. Add broader CI coverage if it is not already wired outside the repo.

## 18. Fast Reference: Files That Matter Most

If you only have time to read a few files, read these first:

- [AGENTS.md](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/AGENTS.md)
- [backend/app/main.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/main.py)
- [backend/app/core/config.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/core/config.py)
- [backend/app/api/v1/api.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/api/v1/api.py)
- [backend/app/models/__init__.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/models/__init__.py)
- [backend/tests/conftest.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/tests/conftest.py)
- [backend/app/domains/auth/router/auth_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/domains/auth/router/auth_router.py)
- [backend/app/domains/participants/router/participant_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/domains/participants/router/participant_router.py)
- [backend/app/infrastructure/storage/router/r2_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/infrastructure/storage/router/r2_router.py)
- [backend/app/partners/router/partner_router.py](/C:/Users/Rikhil%20Nellimarla/Projects/recon-backend/backend/app/partners/router/partner_router.py)

## 19. Final Notes for the Next Agent

This repo is not chaotic, but it is in an active integration phase. The biggest risks are not “hard problems”; they are inconsistent state, partial implementations, and configuration drift.

The recurring pattern is:

- architecture is thought through
- some surfaces are already solid
- several files and docs still lag the actual implementation

So the right posture is:

- read before editing
- do not trust autogenerate blindly
- do not trust status docs blindly when they visibly conflict
- verify route mounts
- verify env expectations
- prefer endpoint tests over isolated internal tests

If you keep those constraints in mind, the codebase is workable.
