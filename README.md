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

- Responsive EN/DE public landing page, navigation, event carousel, and accessible demo dialog.
- UI-only User Login, Student Registration, and direct-URL Admin Login pages with client-side
  validation. These forms do not yet authenticate users.
- Development event fixtures plus a production-shaped event API adapter.
- FastAPI application with generated OpenAPI documentation and a database health endpoint.
- Async SQLAlchemy/PostgreSQL connection boundary with separate runtime and migration credentials.
- Alembic baseline for the private `app_private` schema and least-privilege runtime role.
- Docker Compose service for local PostgreSQL 17 with the pgvector package.
- Shared SQLAlchemy base model and the `USER`/`ADMIN` role contract.
- Exact-origin credentialed CORS configuration.
- Persisted User model/migration, bcrypt and registration/login/role services, hardened JWT cookie
  primitives, and a signed double-submit CSRF bootstrap endpoint.
- CSRF-protected registration and login endpoints. Login returns a sanitized User and establishes
  access/refresh JWTs only in HttpOnly cookies with a session-bound CSRF context.
- Persistent refresh-session state plus a CSRF-protected refresh endpoint with atomic token
  rotation and session-family revocation when an old refresh token is reused.
- A reusable verified-current-user dependency that authenticates the access cookie and reloads
  active User identity and role from PostgreSQL for protected backend routes.
- A no-store `GET /api/auth/me` endpoint that restores only the sanitized current User session.

Not implemented yet:

- Logout endpoint and frontend session integration.
- Frontend registration/login integration and authenticated session bootstrap.
- Protected User/Admin routes backed by server authorization.
- Profile, event-management, matching, notification, or AI business APIs.
- A provisioned production Supabase project or production deployment configuration.

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
- Local infrastructure: Docker Desktop and Docker Compose.
- CI: GitHub Actions runs deterministic frontend and backend checks.

## Repository Structure

```text
.
├── apps/
│   ├── api/                    # FastAPI application, Alembic, tests, Python lockfiles
│   └── web/                    # React/Vite application and frontend tests
├── docs/                       # Repository and implementation audit documents
├── .github/workflows/          # Continuous integration
├── docker-compose.yml          # Local PostgreSQL + pgvector service
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

### Local PostgreSQL

Create an ignored `apps/api/.env` from `apps/api/.env.example`, set a unique local password, and
start PostgreSQL from the repository root:

```sh
docker compose --env-file apps/api/.env config --quiet
docker compose --env-file apps/api/.env up -d --wait postgres
```

Configure `DATABASE_MIGRATION_URL` in the Alembic process, then run:

```sh
cd apps/api
python -m alembic -c pyproject.toml upgrade head
```

Use `docker compose --env-file apps/api/.env down` to stop the database while preserving its named
volume. Do not add `--volumes` unless a destructive local reset is intended.

## Environment Variables

Committed templates:

- [apps/web/.env.example](apps/web/.env.example): frontend API URL, analytics placeholder, and
  development event-fixture flag.
- [apps/api/.env.example](apps/api/.env.example): local Compose values, runtime/migration database
  URLs, auth/CSRF signing keys, cookie policy, and the exact CORS origin allowlist.

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

No production deployment is configured or claimed by this repository. The implementation plan
targets a separately deployed frontend, FastAPI service, and Supabase-hosted PostgreSQL, but those
resources must be provisioned and verified before they can be documented as live.

## Development Status and Roadmap

Backend foundation tasks BE-001 through BE-007 and authentication tasks AUTH-007 through AUTH-019
are complete. AUTH-020 rate limiting and AUTH-024 backend logout have passed local/live acceptance.
AUTH-004's non-persisted frontend session store and AUTH-021 session client/forms/bootstrap are
complete. Session CSRF recovery after reload, bounded single-flight refresh, registration and
targeted logout/account-switch cache clearing are verified (frontend 175 PASS; backend 384 PASS,
10 existing Redis live skips). Real local browser + disposable PostgreSQL registration/login/
reload/logout PASS; AUTH-024's combined frontend/cache acceptance is satisfied. Production
Redis/TLS/ingress smoke remains pending for AUTH-020; no deployed production authentication is
claimed. The next development task is AUTH-005 (ProtectedRoute), not started here; AUTH-006 and
role-specific login routing in AUTH-022/023 remain planned.

See [implementation_plan_vgu_buddy.md](implementation_plan_vgu_buddy.md) for the authoritative task
order and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution conventions.

## Security Note

Never commit credentials. A Gemini credential exposed in the legacy repository remains scheduled
for revocation before any future Gemini/chatbot integration; it is not used by this codebase.
