# VGU Buddy

## Overview

VGU Buddy is a student companion platform for the Vietnamese-German University community. It is
being built to help students discover campus activities, manage their profiles, and eventually find
compatible buddies through a secure matching workflow.

The repository is a monorepo containing a React frontend and a FastAPI backend. The public website
and authentication screens are usable today, while authenticated sessions, domain data, and the
matching workflow are still under active development.

## Current Features

Implemented:

- Responsive EN/DE public landing page, navigation, bundled static Upcoming Events carousel, and
  accessible demo dialog.
- API-connected registration, User/Admin login, session bootstrap/refresh/logout, protected routes,
  exact-role guards, and private-query cleanup.
- Backend-owned bcrypt passwords, rotating JWT cookie sessions, signed double-submit CSRF,
  server-authoritative role checks, rate limiting, and sanitized auth responses.
- PostgreSQL-backed own-profile onboarding/edit/view flows for Vietnamese and international
  students, completion/eligibility calculation, catalogs, and optimistic version checks.
- Private profile-avatar upload, crop/optimization, server-side validation, Supabase Storage, signed
  delivery URLs, removal, and persistence across reload/login.
- Admin-only bounded user/profile reads plus the Admin shell, overview, DataTable and ConfirmDialog.
- Event tables and CRUD/publication service contracts. These services are not yet exposed as Event
  API routes.
- Async SQLAlchemy/PostgreSQL access, Alembic migrations through `0007_event_tables`, private
  `app_private` schema, least-privilege runtime role, database health probe, and local PostgreSQL 17.

Not implemented yet:

- Buddy Matching persistence, algorithm, APIs, delivered User pages, or Admin matching workflow.
- Production Event/Event Slider APIs and the remaining Admin/public Event UI.
- Notifications, AI assistant, campus, and settings business features.
- Provisioned production backend/Redis/database/storage environments and verified same-site ingress.

## Architecture

```text
Browser
   │
   ▼
React + TypeScript + Vite (apps/web)
   │  HTTP /api
   ▼
FastAPI (apps/api)
   ├── Credentialed CORS
   ├── Database health endpoint
   └── SQLAlchemy async + asyncpg
          │
          ▼
PostgreSQL selected by environment
   ├── Local: Docker Compose, PostgreSQL 17 + pgvector package
   └── Cloud: Supabase-hosted PostgreSQL is planned, not configured here

Alembic ── DATABASE_MIGRATION_URL ──► app_private schema
FastAPI ── DATABASE_URL ────────────► least-privilege runtime role
```

FastAPI remains the planned authentication authority. The project does not use Supabase Auth, and
the repository does not contain a Supabase Local stack.

## Tech Stack

- Frontend: React 19, TypeScript, Vite, React Router, TanStack Query, Zustand, Tailwind CSS, i18next.
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2, asyncpg, Alembic, Pydantic.
- Database: PostgreSQL 17; the local image includes pgvector 0.8.6.
- Testing and quality: Vitest, Testing Library, ESLint, Prettier, pytest, Ruff, mypy, pip-audit.
- Local infrastructure: Docker Desktop and Docker Compose for the reproducible full stack.
- CI: GitHub Actions runs deterministic frontend and backend checks.

## Repository Structure

```text
.
├── apps/
│   ├── api/                    # FastAPI application, Alembic, tests, Python lockfiles
│   └── web/                    # React/Vite application and frontend tests
├── docs/                       # Repository and implementation audit documents
├── .github/workflows/          # Continuous integration
├── docker-compose.yml          # Local PostgreSQL, Redis, API, worker and web stack
├── implementation_plan_vgu_buddy.md
└── CONTRIBUTING.md
```

## Local Development

### Prerequisites

- Node.js 22.12 or newer and npm. Node.js 24 is used by CI.
- Python 3.12 or newer. Python 3.12 is used to resolve lockfiles and run CI.
- Docker Desktop only when a local PostgreSQL database is needed.

### Frontend

```sh
cd apps/web
npm ci
npm run dev
```

The current-launch Upcoming Events carousel uses typed, bundled frontend content in every
environment and makes no Event API request. Copy `apps/web/.env.example` to an ignored
`apps/web/.env.local` only when local overrides are needed.

### Backend

Create a virtual environment in `apps/api`, then install the deterministic development dependency
set and the local package without re-resolving dependencies:

```sh
cd apps/api
python3.12 -m venv .venv
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
uvicorn app.main:app --reload
```

On Windows, `py -3.12 -m venv .venv` can be used instead of `python3.12 -m venv .venv`.

For a runtime-only environment, install `requirements.lock` instead of
`requirements-dev.lock`. See [apps/api/README.md](apps/api/README.md) for database credentials,
migrations, and the health check.

### Reproducible local stack

Create an ignored `apps/api/.env` from `apps/api/.env.example`. Supply unique local-only database,
auth, CSRF and sealing secrets plus sandbox Storage/email settings. For Compose, both database URLs
must use the internal host `postgres`; `DATABASE_URL` remains the least-privilege runtime role and
must use `LOCAL_RUNTIME_DATABASE_PASSWORD`, while `DATABASE_MIGRATION_URL` remains the privileged
migration role. Never commit this file.

Create the ignored localhost certificate bundle once, then trust only its public local CA in the
current user's development trust store. On Windows PowerShell:

```powershell
apps/api/.venv/Scripts/python.exe scripts/generate_local_tls.py
certutil -user -addstore Root .local/tls/vgu-buddy-local-ca.crt
```

The CA private key remains under ignored `.local/tls` and must never be reused for staging or
production. Local browser traffic uses one origin, `https://localhost:5173`; Vite terminates TLS and
proxies `/api` (including WebSocket upgrades) to the internal API service. The backend keeps the
HTTPS-only verification-link invariant and uses Secure cookies locally.

From the repository root, validate and start PostgreSQL, Redis, migration, API, leased outbox
worker and Vite web server with one command set:

```sh
docker compose --env-file apps/api/.env config --quiet
docker compose --env-file apps/api/.env up --build -d --wait
```

Run this command from the repository root without a different project name. Compose then uses the
directory-derived `buddywebver2` project and preserves the existing `buddywebver2_postgres_data`
volume.

All published ports bind to loopback. API liveness is `/api/health/live`; readiness is
`/api/health/ready` and reports separate sanitized database, Redis, email and Storage states.
The worker reuses PostgreSQL outbox leases after restart. Redis outages fail the API readiness
probe without exposing connection details, while Compose restart policy recovers failed processes.

Stop the stack while preserving PostgreSQL and Redis named volumes:

```sh
docker compose --env-file apps/api/.env down
```

Do not add `--volumes` unless a destructive local reset is intended. To run only infrastructure
for host-based development, start `postgres redis` and follow the backend README for migrations and
the local runtime-role password.

## Environment Variables

Committed templates:

- [apps/web/.env.example](apps/web/.env.example): frontend API URL, analytics placeholder, and
  dormant post-deployment dynamic Event settings. The static Landing carousel ignores both Event
  variables and is part of the current release. `VITE_EVENTS_LAUNCH_ENABLED` gates only future
  API-backed User/Admin Event surfaces; keep it `false` until the deferred Part 27 work and
  `ACCEPT-EVENT-001` are complete.
- [apps/api/.env.example](apps/api/.env.example): local Compose values, runtime/migration database
  URLs, shared Redis namespaces, auth/CSRF signing keys, cookie policy, and exact CORS origins.

Populated `.env` files are ignored. Database passwords and URLs are server-only and must never use a
`VITE_` prefix or be committed.

## Testing and Quality Gates

Frontend, from `apps/web`:

```sh
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
npm audit --omit=dev
```

Backend, from `apps/api`:

```sh
python -m pip check
ruff check .
mypy app tests
pytest
python -m alembic -c pyproject.toml history
python -m alembic -c pyproject.toml heads
python -m build --no-isolation
python -m pip_audit -r requirements.lock
```

Regenerate the Python lockfiles after an intentional dependency change:

```sh
python -m piptools compile --allow-unsafe --strip-extras --output-file requirements.lock pyproject.toml
python -m piptools compile --allow-unsafe --extra dev --strip-extras --output-file requirements-dev.lock pyproject.toml
```

## Deployment

`apps/web/vercel.json` provides the required Vite SPA deep-link fallback and baseline browser
security headers. Configure the Vercel project Root Directory as `apps/web`, set `VITE_API_URL` at
build time, and keep every server secret out of `VITE_*` variables.

The FastAPI deployment runs from `apps/api` with a command equivalent to
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Production uses operator-provided PostgreSQL,
migration, TLS Redis, Supabase Storage and exact CORS/CSRF origins. Because authentication
uses host-only `SameSite=Lax` cookies, frontend and API must be deployed on the same site (for example,
first-party subdomains or a reviewed reverse proxy); an unrelated Vercel-to-backend origin is not an
accepted production topology.

Email verification additionally requires a server-only `EMAIL_VERIFICATION_SEALING_KEY` in both
the API and email worker plus an exact HTTPS `PUBLIC_APP_BASE_URL`; neither value belongs in `VITE_*`.

Hosted transactional email uses the existing PostgreSQL outbox through **Supabase Cron -> Supabase
Edge Function -> Resend**. It does not require a Google Cloud VM or paid Render worker. The Python
worker remains available for local development, debugging and fallback, but must not run alongside
the hosted Cron schedule. Deployment, secrets and acceptance are documented in
[docs/operations/supabase-email-worker.md](docs/operations/supabase-email-worker.md).

Initial production has deliberately selected a separate **Render Free** API service with separate
Supabase, TLS Redis, Storage and secret configuration. Its cold-start/resource limits are accepted
operational risk. For the progress-reporting MVP, full `ACCEPT-001` sign-off and the complete DR
rehearsal remain OPEN post-deploy hardening rather than automatic release blockers; isolated
resources, safe migration, production secrets, health and core-flow smoke tests remain mandatory.
The dated reclassification is in
[docs/operations/production-mvp-readiness-2026-10-07.md](docs/operations/production-mvp-readiness-2026-10-07.md).
Capacity gates, temporary-host verification, paid-reevaluation criteria and the DNS/rollback order are in
[docs/operations/render-free-production.md](docs/operations/render-free-production.md). Scheduled
retention and full off-site recovery are documented separately in
[docs/operations/supabase-maintenance-worker.md](docs/operations/supabase-maintenance-worker.md) and
[docs/operations/supabase-free-offsite-dr.md](docs/operations/supabase-free-offsite-dr.md).

The maintenance scheduler passed staging acceptance on 2026-10-04 for commit `5b20c00`: Supabase
Cron health succeeded across at least two intervals, and Render emitted sanitized completion events
for invitation expiry, chat cleanup and semester-backup expiry. The redacted evidence is in
[docs/operations/maintenance-staging-evidence-2026-10-04.md](docs/operations/maintenance-staging-evidence-2026-10-04.md).

The progress-reporting MVP is now deployed on the first-party topology. A direct read-only check on
2026-10-08 confirmed `www.vgubuddyprogram.com` on Vercel, `api.vgubuddyprogram.com` on Render,
dependency-aware readiness, the deployed first-party API target, anonymous auth no-store behavior and
exact-origin CORS. Authenticated Admin/core Buddy/WSS smoke and the release hold/rollback record are
still required before `PROD-001` can be closed. Current evidence is summarized in
[docs/implementation/production-status.md](docs/implementation/production-status.md).

OPS-002 staging topology, backup/rollback rehearsal, WSS and end-to-end smoke requirements are in
[docs/operations/ops-002-staging-validation.md](docs/operations/ops-002-staging-validation.md).

## Development Status and Roadmap

Buddy Matching V2, email verification/outbox, preferences/recommendations, invitation/Current Buddy,
chat, Admin monitoring and safeguarded Semester management are implemented. The reporting MVP is
deployed, but `PROD-001` remains IN PROGRESS until authenticated Production smoke, hold monitoring
and rollback evidence are complete. Residual `ACCEPT-001` and full encrypted DR evidence remain
explicit post-deployment hardening.

The current execution order and verified continuation point live in
[implementation-plan.md](implementation-plan.md) and [SESSION_HANDOFF.md](SESSION_HANDOFF.md).
Use [docs/implementation/task-index.md](docs/implementation/task-index.md) for one-task extracts;
the former [complete plan](implementation_plan_vgu_buddy.md) is a legacy archive, not the current
task router. Dynamic Event/Admin Event work remains deferred and feature-gated.

Development, commits and normal pushes use `main` directly unless repository protection or a user
request requires another workflow; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Security Note

Never commit credentials. A Gemini credential exposed in the legacy repository remains scheduled
for revocation before any future Gemini/chatbot integration; it is not used by this codebase.
