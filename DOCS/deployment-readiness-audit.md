# Deployment Readiness Audit — Recon Backend

## Purpose

This document is a deployment-readiness handoff for the debug team. It is based on the current backend implementation in `recon-backend`, not on an idealized architecture.

The goal is to identify:

- what is safe to ship now
- what is unsafe in production
- what exists only because of temporary developer setup
- what must be fixed before event traffic
- what is optional and can wait until after the event

Target operating context:

- around 600 concurrent users
- short event window with bursty traffic
- AWS deployment, likely ECS Fargate
- Neon Postgres
- Upstash Redis
- Cloudflare in front of AWS
- Cloudflare R2 / S3-compatible object storage

---

## Executive Summary

The current backend is close to a workable event MVP, but it is not yet production-ready.

The main blockers are not scale theory problems. They are practical deployment and security issues in the current code:

1. Object storage access control is broken for read URLs.
2. Production auth configuration still contains temporary/copy-pasted values from another project.
3. Session and OAuth hardening are incomplete.
4. There is no rate limiting on sensitive endpoints.
5. Neon connection pressure can become a real issue during burst traffic.
6. CI/CD and deploy safety are not yet defined in-repo.

If those areas are fixed, the backend can be deployed as a single API service on Fargate without introducing workers or extra operational complexity.

---

## Current Runtime Shape

### Active mounted API domains

The current API mounts only:

- auth
- incidents
- participants
- storage / R2
- partners

The router composition is in `backend/app/api/v1/api.py`.

### Present but not live yet

The repo also contains code for:

- announcements
- realtime websocket announcements
- zones
- points
- schedule
- teams
- shop
- webhooks
- admin

Most of those are not mounted into the running API right now. They should not drive immediate deployment complexity decisions.

### Stateful vs stateless

The application container is stateless.

Persistent state lives in:

- Neon Postgres
- Upstash Redis
- Cloudflare R2

This is good for Fargate. No local disk assumptions were found in the active request paths.

---

## Recommended Deployment Topology

### Recommended now

Use:

- 1 ECS service for the API
- 1 container image
- 2 running tasks minimum
- tasks spread across 2 AZs
- ALB as AWS origin
- Cloudflare in front of ALB

This is enough for the currently mounted backend.

### Do not add a worker service yet

A separate worker or queue service is not justified by the code that is actually live:

- no Celery
- no RQ
- no Dramatiq
- no arq
- no background job ownership model
- no required async offload path in active routers

Adding workers now would be premature architecture.

### Separate migration task

Do create a separate ECS one-off task for Alembic migrations during deploy.

Do not rely on application startup to apply schema changes.

### Future split only if realtime becomes active

If websocket announcements are mounted later, split into:

- API service
- websocket/realtime service

Reason:

- long-lived connections scale differently from request/response traffic
- websocket autoscaling and health behavior are different
- Redis pub/sub use for websockets should not interfere with normal API capacity planning

---

## Production Architecture Recommendation

### AWS path

Recommended flow:

`Client -> Cloudflare -> ALB -> ECS Fargate API tasks -> Neon / Upstash / R2 / Logfire`

### Why this is the right level of complexity

This system is short-lived, event-specific, and bursty. Operational simplicity matters more than maximizing infrastructure cleverness.

That means:

- prefer Fargate over EC2
- prefer one API service over many microservices
- prefer ALB over API Gateway
- prefer Cloudflare only, not Cloudflare plus CloudFront

---

## Critical Security Findings

## 1. R2 read URL access control is unsafe

### What is happening

`/api/v1/r2/read-url` lets any authenticated user request a presigned download URL for any `file_key` that matches the storage key regex.

The endpoint does not verify:

- ownership
- object type
- whether the object belongs to the requesting user
- whether the object belongs to a public or private namespace

### Why this is exploitable

The file key is exposed in normal API responses:

- participant responses expose `profile_photo_file_key`
- partner asset responses expose `file_key`

That means one authenticated user can learn another user’s file key and then mint a signed read URL for that object.

### Risk

High. This is a real production data exposure path, not a theoretical issue.

### Required fix

Choose one explicit object access model.

Recommended model:

- public assets: no presigned read URL endpoint needed
- private user-owned assets: check ownership before signing
- admin-only assets: require admin role before signing

### Concrete remediation

1. Split storage keys by namespace:
   - `public/...`
   - `participants/{user_id}/...`
   - `partners/{partner_id}/...`
   - `admin/...`
2. Replace regex-only validation with authorization-aware lookup.
3. For participant photo reads:
   - allow owner
   - allow admin
   - optionally allow public only if the photo is intentionally public
4. For partner asset reads:
   - allow partner owner
   - allow admin
   - allow public only if asset is marked public
5. Stop returning raw private `file_key` values to users who do not need them.

### Temporary dev shortcut involved

This looks like a convenience implementation for early integration. It is not safe to keep in production.

---

## 2. Production auth config still contains temporary project values

### What is happening

Current config and middleware still reference another project/domain:

- production CORS allowlist uses `traction-ai.me`
- production OAuth redirect defaults to `api.traction-ai.me`
- Google callback redirects to `/test.html`

### Risk

High. This can break login in production or redirect users to incorrect locations.

### Required fix

Move all environment-dependent URLs into explicit production config.

### Concrete remediation

1. Add explicit settings:
   - `APP_BASE_URL`
   - `API_BASE_URL`
   - `FRONTEND_REDIRECT_AFTER_LOGIN`
   - `ALLOWED_ORIGINS`
2. Remove project-specific hardcoded domains from source.
3. Fail fast on startup if required production URL settings are missing.
4. Add a deploy smoke test for:
   - Google login redirect
   - callback success
   - cookie issuance
   - frontend redirect

### Temporary dev shortcut involved

Yes. This is classic copied bootstrap config used during initial development. It is unsafe if left in place.

---

## 3. Session middleware is under-hardened for production

### What is happening

OAuth state depends on `SessionMiddleware`, but the middleware is currently added with only a secret key.

The code does not explicitly enforce:

- HTTPS-only session cookie
- strict cookie name choices
- same-site policy chosen for OAuth flow
- trusted host policy

### Risk

Medium to high depending on final domain setup and whether HTTPS termination and proxy headers are handled correctly.

### Required fix

Explicitly harden session cookie behavior for production.

### Concrete remediation

1. Configure:
   - `https_only=True`
   - `same_site="lax"` unless a cross-site frontend flow requires a different setting
   - a non-default cookie name
   - short session lifetime
2. Ensure proxy/forwarded headers are correctly handled behind ALB and Cloudflare.
3. Add `TrustedHostMiddleware`.
4. Add security headers at Cloudflare or app layer:
   - HSTS
   - X-Frame-Options
   - X-Content-Type-Options
   - Referrer-Policy

### Temporary dev shortcut involved

Partly. Minimal middleware setup is normal in development, but unsafe as a production default.

---

## 4. Hardcoded admin bootstrap emails are dangerous

### What is happening

The app boot process:

- creates roles
- assigns missing default roles
- upgrades matching emails to admin

This happens automatically during application startup.

### Risk

High operational risk.

Examples:

- accidental prod access if the wrong env file is used
- confusion between staging and production identities
- repeated role mutation on every deploy
- hidden privilege behavior outside normal admin workflows

### Required fix

Remove boot-time privilege assignment from normal app startup for production.

### Concrete remediation

Recommended:

1. Keep role creation migration-safe if needed.
2. Move admin bootstrap into a manual one-off admin script or migration.
3. Require explicit environment flag if bootstrap is ever allowed:
   - `ENABLE_ADMIN_BOOTSTRAP=false` in production by default
4. Log any privilege bootstrap event loudly.

### Temporary dev shortcut involved

Yes. This is a temporary developer convenience and should be treated as unsafe in production.

---

## 5. Public health endpoint leaks internal DB error text

### What is happening

`/db_check` is public and returns raw exception text when the DB is unhealthy.

### Risk

Medium. Not the worst issue, but it leaks internals that external users do not need.

### Required fix

Split health checks by purpose.

### Concrete remediation

1. Public liveness endpoint:
   - returns only `200 ok`
2. Internal readiness endpoint:
   - checks DB and Redis
   - accessible only from ALB health checks or internal network
3. Never return raw DB exception text to public clients.

### Temporary dev shortcut involved

Yes. This is acceptable during local debugging, not in production.

---

## 6. No rate limiting on sensitive endpoints

### What is happening

There is currently no app-level or proxy-level rate limiting in the backend code.

### Risk

High during the event.

The most sensitive endpoints are:

- `/auth/google/login`
- `/auth/google/callback`
- `/auth/refresh`
- `/incidents/`
- `/r2/upload-url`

Without rate limiting:

- login endpoints can be abused
- refresh endpoints can be hammered
- incident reporting can be spammed
- presign endpoints can be used to create storage abuse pressure

### Required fix

Add layered rate limiting:

- Cloudflare for coarse IP-based filtering
- Upstash/Redis for application-aware limits

### Concrete remediation

Recommended keys:

- anonymous: `rl:{route}:{ip}`
- authenticated: `rl:{route}:user:{user_id}`
- sensitive auth: `rl:{route}:user:{user_id}:ip:{ip}`

Recommended limits:

- login start: 10/min/IP
- refresh: 30/min/user, 60/min/IP
- incident create: 5/min/user, 20/min/IP
- upload URL minting: 10/min/user, 30/hour/user
- admin polling endpoints: 120/min/user

Implementation notes:

1. Build a FastAPI dependency for per-route limiting.
2. Use Redis sorted-set sliding window or Lua token bucket.
3. Fail open for cache-only paths if Redis is degraded.
4. Fail carefully on abuse-sensitive auth endpoints.

### Temporary dev shortcut involved

Yes. The repo explicitly says rate limiting is not yet implemented. That is acceptable during development, unsafe for event production.

---

## Validation and Input Safety Gaps

## 1. Live write schemas are too permissive

### What is happening

Active write schemas accept plain unconstrained strings for many fields:

- participant profile fields
- partner application fields
- incident title and description

The DB model has some max lengths, but the API layer should reject bad input before it reaches the DB.

### Risks

- noisy 500/DB errors instead of clean 4xx responses
- oversized payload abuse
- weak data hygiene
- inconsistent validation behavior

### Required fix

Add request-level validation in schemas.

### Concrete remediation

Use constrained fields for:

- title lengths
- free-text max lengths
- display names
- phone format
- URL fields
- email fields
- optional social handles

Also add:

- `min_length`
- `max_length`
- `pattern` where appropriate
- explicit body size limit at ALB/Cloudflare or app middleware

### Temporary dev shortcut involved

Yes. Loose schema validation is typical during initial buildout, but should not survive into production.

---

## 2. Storage upload validation is incomplete

### What is happening

Upload URL generation validates:

- extension
- claimed content type

But it does not verify the uploaded object after upload.

Also, `ContentLength` inside presign parameters is not a strong end-to-end security control by itself.

### Risks

- content-type spoofing
- mislabeled files
- malware or unwanted content stored in R2

### Required fix

Treat presign as upload authorization, not file trust.

### Concrete remediation

1. Keep extension/content-type allowlist.
2. Add object metadata recording after upload.
3. Add post-upload verification if files matter operationally.
4. If practical, use a callback or manual confirmation step before persisting file references to domain objects.
5. Consider antivirus scanning only if threat model requires it; for this event, simple strict allowlisting plus access control may be enough.

### Temporary dev shortcut involved

Partly. Presign-only validation is common in early development but should be recognized as incomplete.

---

## Database and Performance Risks

## 1. Neon connection exhaustion is a real risk

### What is happening

Every authenticated request reads the user from the database after JWT verification.

That means auth is not purely token-local. Under load:

- each active API task opens a small pool
- every request can still produce DB activity
- admin dashboards that poll repeatedly will increase DB load

### Why this matters

At event bursts, connection pressure can hurt availability faster than raw CPU usage.

### Required fix

Tune for Neon specifically.

### Concrete remediation

1. Use Neon pooled connection endpoint, not direct connections.
2. Keep SQLAlchemy pool conservative:
   - `pool_size=3 to 5`
   - `max_overflow=0 to 2`
   - explicit `pool_timeout`
3. Start with 2 ECS tasks and measure connection count before scaling wider.
4. Cache admin list endpoints with short TTLs.
5. Avoid introducing more synchronous DB lookups inside auth middleware.

### Temporary dev shortcut involved

No. This is a deployment tuning issue rather than a developer convenience issue.

---

## 2. Some list queries need indexes for event usage

### Current state

The current schema includes useful base indexes:

- user email
- username
- participant display name
- participant user_id
- partner user_id
- incident assigned/reported fields
- refresh token hash

### Missing indexes that are likely worth adding

Add:

- `participants (checked_in_at, created_at desc)`
- `partners (status, created_at desc)`
- `incidents (status, severity, created_at desc)`

These match current admin list/filter behavior and reduce sort-plus-filter work during polling.

### Temporary dev shortcut involved

No. This is normal index maturation.

---

## 3. No obvious N+1 in active endpoints

### Current assessment

The active code does not show a serious N+1 issue in the live paths:

- auth uses joined role loading
- partner list uses selectinload for incentives and assets

### Practical conclusion

Do not spend time solving imaginary ORM problems before the event. Focus on connection pressure, polling behavior, and missing indexes first.

---

## Caching Strategy

## CDN cache

Use Cloudflare CDN caching for:

- frontend static assets
- public media assets only

Do not CDN-cache current API endpoints by default because they are:

- authenticated
- cookie-based
- user-specific
- operationally sensitive

## Redis cache

Cache only the endpoints most likely to be polled:

- admin participant list
- admin incident list
- admin partner list

Recommended TTLs:

- participant list: 10 to 15 seconds
- incident list: 5 to 10 seconds
- partner list: 30 seconds

Invalidation:

- participant create/update/check-in clears participant list cache
- incident create/update clears incident list cache
- partner apply/review/incentive/asset mutation clears partner cache

## Do not cache

Do not cache:

- `/auth/me`
- `/participants/me`
- `/participants/{id}`
- `/partners/me`
- `/auth/refresh`
- `/auth/logout`
- `/r2/upload-url`
- `/r2/read-url`

## Why short TTL cache still helps

Even a 5 to 15 second cache can dramatically reduce repeated dashboard polling load on Neon during the event.

---

## Realtime and Websocket Notes

There is websocket code for announcements, but it is not part of the mounted API right now.

This means:

- do not build deployment complexity around it yet
- do not optimize for websocket scale before it is actually live
- if enabled later, isolate it from the API service

Also note:

- the websocket code currently accepts connections without auth checks
- it uses Redis pub/sub directly

If realtime is made live, it needs its own security review.

---

## CI/CD Recommendation

## Pipeline stages

Recommended production pipeline:

1. install dependencies with `uv`
2. run tests
3. build container image
4. tag image with git SHA
5. push image to ECR
6. run Alembic migration task
7. deploy ECS service update
8. run smoke tests
9. keep rollback target ready

## Tagging strategy

Use:

- immutable git SHA tag
- optional release tag for human readability

Do not deploy mutable-only tags like `latest`.

## Deployment strategy

For this repo, use rolling deploy.

Why:

- simpler to operate
- enough for current single-service shape
- lower coordination cost than blue-green

Blue-green is only worth it if you rehearse it. Unrehearsed blue-green is fake safety.

## Deployment safety requirements

Before prod deploys, add smoke tests for:

- root health
- readiness
- Google auth redirect path
- Google callback and cookie set
- one authenticated request
- one storage presign request

---

## Failure Modes and Mitigations

## 1. DB connection exhaustion

### What breaks

- login/me endpoints start failing
- authenticated APIs degrade broadly
- admin dashboards fail first under polling

### Mitigation

- use Neon pooler
- keep app pool small
- cache admin list views
- run 2 warm tasks
- load test before event

## 2. Redis or Upstash latency spike

### What breaks

- cache responses slow down or miss
- future rate limiting becomes unreliable if badly implemented
- websocket/pubsub would be noisy if enabled

### Mitigation

- fail open for non-critical cache reads
- fail carefully for abuse controls
- instrument Redis latency separately

## 3. OAuth misconfiguration during deploy

### What breaks

- login loop
- callback failure
- cookies not issued
- frontend stuck after auth

### Mitigation

- remove hardcoded external domains from source
- add deploy smoke tests
- maintain staging environment with real OAuth credentials

## 4. Single-task outage

### What breaks

- entire event API goes down on one bad task or AZ issue

### Mitigation

- minimum 2 tasks
- 2 AZ placement
- health checks and fast rollback

## 5. IAM or R2 secret misconfiguration

### What breaks

- upload URL generation fails
- read URL generation fails
- partner and participant media flows fail

### Mitigation

- startup validation for required env vars
- synthetic presign probe in staging
- scoped credentials

---

## Cost Traps

## 1. NAT Gateway can silently burn credits

This is the most likely hidden AWS bill problem.

If Fargate tasks run in private subnets and need outbound internet for:

- Neon
- Upstash
- Logfire
- Google OAuth

then NAT gateway charges can add up quickly.

### Recommendation

Be deliberate about network design. For an event system, simple public-subnet Fargate with locked-down security groups may be cheaper and operationally easier than private-subnet plus NAT.

## 2. Over-scaling Fargate tasks

Fargate is fine here, but idle overprovisioning still costs money.

### Recommendation

- start with 2 tasks
- modest CPU/memory
- scale based on measured load, not fear

## 3. Poll-heavy dashboards

This is both a DB cost and observability cost trap.

### Recommendation

- short TTL cache
- avoid aggressive frontend polling
- prefer backoff when idle

## 4. Redundant edge stack

Cloudflare plus CloudFront is unnecessary here.

### Recommendation

Use Cloudflare only unless a very specific AWS-native requirement appears.

---

## Temporary Developer Config and Shortcuts That Are Unsafe in Production

This section is explicit so the debug team can separate intentional MVP shortcuts from actual production-safe defaults.

### Unsafe temporary items

1. Hardcoded prod URLs and copied domain references in config.
2. Redirecting OAuth callback to `/test.html`.
3. Boot-time admin email promotion.
4. Public `/db_check` with raw error text.
5. No rate limiting.
6. Minimal session middleware hardening.
7. Regex-only authorization for storage reads.
8. Loose request schemas without strong API-layer constraints.

### Temporary items that are acceptable only if explicitly contained

1. Minimal Redis cache layer with few active callers.
2. Single-service API deployment shape.
3. No background workers.
4. Realtime code present but not mounted.

These are not unsafe by themselves. They are only unsafe if people assume they are already production-complete.

---

## What Should Be Fixed Before The Event

## Blockers

1. Fix storage read authorization.
2. Remove copied production URLs and finalize real OAuth/callback config.
3. Harden session and cookie behavior.
4. Remove or gate admin bootstrap behavior.
5. Implement rate limiting.
6. Finalize Neon pooling strategy and load test it.
7. Add deploy smoke tests and rollback process.

## Strongly recommended before event

1. Add request validation constraints.
2. Split public vs private health endpoints.
3. Add short-TTL cache for admin list views.
4. Add the missing list/filter indexes.

## Can wait until after event

1. Splitting realtime into a separate service, unless it becomes live.
2. Blue-green deployment.
3. More advanced async job architecture.
4. ElastiCache migration.

---

## Suggested Debug Team Action Plan

## Phase 1: Security and auth correctness

1. Fix R2 read authorization.
2. Fix all prod URL and redirect settings.
3. Harden session cookie config.
4. remove boot-time admin bootstrap from normal prod startup.

## Phase 2: deploy safety

1. Add container build and ECS deploy workflow.
2. Add migration task.
3. Add smoke tests.
4. Add rollback steps.

## Phase 3: event load readiness

1. Implement rate limiting.
2. Add short-TTL admin caches.
3. Add indexes.
4. load test auth plus dashboard polling.

## Phase 4: cleanup

1. tighten schema validation
2. improve health endpoints
3. document runbooks for outage scenarios

---

## Final Recommendation

Do not overengineer this backend into multiple services before the event.

The correct production move is:

- one API service
- two Fargate tasks
- ALB behind Cloudflare
- Neon pooler
- Upstash for rate limiting and short TTL caches

But do not ship the current code unchanged.

The unsafe parts are mostly temporary developer-era shortcuts that now need to be removed or explicitly gated for production. The most important one is storage access control. The next most important are auth config drift, missing rate limits, and deployment hardening.
