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

- Responsive EN/DE public landing page, navigation, development event carousel, and accessible demo
  dialog.
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

The development event fixtures work without a backend. Copy `apps/web/.env.example` to an ignored
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
  development event-fixture flag.
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

The FastAPI deployment must run from `apps/api` with a command equivalent to
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Production still requires operator-provided
PostgreSQL, migration, TLS Redis, Supabase Storage and exact CORS/CSRF origins. Because authentication
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

The repository is suitable for a staging deployment after those environment resources are supplied,
but no production deployment is configured or claimed.

OPS-002 staging topology, backup/rollback rehearsal, WSS and end-to-end smoke requirements are in
[docs/operations/ops-002-staging-validation.md](docs/operations/ops-002-staging-validation.md).

## Development Status and Roadmap

Backend foundation tasks BE-001 through BE-007 and authentication tasks AUTH-007 through AUTH-019
are complete. AUTH-020 rate limiting and AUTH-024 backend logout have passed local/live acceptance.
AUTH-004's non-persisted frontend session store and AUTH-021 session client/forms/bootstrap are
complete. Session CSRF recovery after reload, bounded single-flight refresh, registration and
targeted logout/account-switch cache clearing are verified (frontend 175 PASS; backend 384 PASS,
10 existing Redis live skips). Real local browser + disposable PostgreSQL registration/login/
reload/logout PASS; AUTH-024's combined frontend/cache acceptance is satisfied. Production
Redis/TLS/ingress smoke remains pending for AUTH-020; no deployed production authentication is
claimed. AUTH-005 ProtectedRoute is complete: unknown/loading sessions show neutral pending;
confirmed anonymous User/Admin routes redirect to their login pages and authenticated sessions
render nested routes. Bootstrap defers refreshed identity until `/me` finishes. Current frontend
**321 tests PASS**, including 31 authentication, 50 role guard, 31 User login and 34 Admin login flow checks. AUTH-006
RoleGuard is complete: User routes require USER, Admin routes require ADMIN; wrong-role requests
replace history with public `/` without private rendering or logout. Final `/me` role governs
bootstrap, and verified refresh role changes remove incompatible content and private cache.
Real local browser cookies/database acceptance covers both roles, matching deep-link reload,
cross-role denial retaining sessions, EN/DE and logout/re-entry; browser error console is empty.
AUTH-022 User login role routing is complete: successful login and recovered sessions at `/login`
replace history with `/user/profile/edit` for USER or `/admin/dashboard` for ADMIN, using only verified
sanitized identity. Pending/failed verification stays on login with safe validation/error/retry;
query/hash/router state/stale storage never choose the destination. Late and superseded responses,
logout/account-switch/private-public cache and real local browser EN/DE acceptance PASS.
AUTH-023 Admin login is complete: validated ADMIN routes to `/admin/dashboard`; a newly issued
USER session at `/adminLogin` is never installed and is logged out with session CSRF before
public denial at `/`. Failed cleanup exposes safe manual logout retry and keeps local identity
cleared. Existing verified USER entry is denied publicly while preserving its established session.
Real local browser/API/database ADMIN and EN/DE USER denial/revocation acceptance PASS.
FE-021 UserLayout is complete: responsive sidebar/content regions, nested route Outlet, one main
landmark, keyboard skip link and EN/DE labels reuse the existing design system. Guard/bootstrap/
logout acceptance and actual desktop/mobile browser checks PASS. FE-022 adds scoped EN/DE student
navigation with current-route semantics. Edit Profile is the first released destination, followed
by My Profile; Dashboard is no longer shown and `/user/dashboard` safely redirects to the editor.
The router and navigation share page-delivery metadata. The editor reuses all three profile/onboarding
forms without duplicating their state. Backend authorization remains authoritative. ADMIN-001 completes the AdminLayout shell with a
distinct dark sidebar, Admin badge, responsive content region, nested Outlet and EN/DE landmarks.
One main and keyboard skip-to-content are verified with guarded reload/logout acceptance. Admin
module navigation is now complete in ADMIN-002: eleven localized native links share the router's
canonical module registry, with current-route semantics and responsive keyboard access. The missing
Event Sliders destination is a guarded scaffold; module business pages remain under development.
ADMIN-003 delivers the Dashboard overview with six accessible EN/DE stats cards. Values explicitly
remain unavailable; no operational totals or stats API are supplied by these placeholders.
ADMIN-004 supplies a reusable client-side DataTable with typed columns/custom cells, localized
sort/filter/search/pagination and caller loading/error/empty states. Its isolated synthetic browser
checks verify keyboard access and responsive scrolling; domain list/API integration remains future work.
Avatar selection now validates extension, MIME and signature before opening an accessible 1:1 crop
dialog. Browser-side reposition/zoom produces an 800×800 WebP (PNG fallback) before the existing
server-side decode, dimension, signature and metadata-stripping validation. No image-processing
service or client-side storage credential was added.

Frontend verification now totals 498 PASS. Source audit on 2026-09-23 confirms that Buddy Matching
has only profile eligibility inputs and guarded placeholder routes; it has no runtime model,
migration, service or API. The next development task is **MATCH-001 — Match model and persistence
constraints**, followed by eligibility, deterministic scoring/assignment, matching APIs and the
User/Admin UI vertical slice.

From FE-022 onward, development, commits and normal pushes use `main` directly unless actual
repository protection prevents it; see [CONTRIBUTING.md](CONTRIBUTING.md).

See [implementation_plan_vgu_buddy.md](implementation_plan_vgu_buddy.md) for the authoritative task
order and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution conventions.

## Security Note

Never commit credentials. A Gemini credential exposed in the legacy repository remains scheduled
for revocation before any future Gemini/chatbot integration; it is not used by this codebase.
