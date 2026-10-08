# AUTH-009

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-008

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2726-2812

### AUTH-009 — Create Alembic migration for users table

**Status**: Completed (✅) on 2026-09-16
**Objective**: Persist the AUTH-008 User metadata through one reversible Alembic revision while
preserving the private-schema, least-privilege and FastAPI-owned authentication boundaries.

The registry supplied the task title, priority and AUTH-008 dependency but no dedicated task
contract. The operational acceptance criteria below define the migration and security behavior
required before password/authentication services can depend on the users table.

**Operational Acceptance Criteria**:

- [x] One linear revision after `0001_private_app_schema` creates the private `user_role` enum and
  `users` table with all AUTH-008 columns, defaults, constraints and indexes.
- [x] The migration creates exactly `USER` and `ADMIN`, defaults role to `USER`, active to true and
  email verification to false, and keeps `last_login`/`deleted_at` nullable and timestamps
  timezone-aware.
- [x] Email uniqueness, non-blank email/hash checks, UUID primary key and deterministic object names
  match SQLAlchemy metadata; the unique constraint supplies the email index without duplication.
- [x] `PUBLIC`, `anon`, `authenticated` and `service_role` receive no users-table or enum access;
  `vgu_buddy_runtime` receives only table CRUD and enum usage.
- [x] RLS is enabled as defense in depth with one permissive all-row policy scoped only to the
  backend runtime role. No Supabase JWT/`auth.uid()` assumption is introduced.
- [x] Alembic reflection is limited to the owned `app_private` schema/tables so drift checks do not
  inspect or propose deletion of Supabase-managed schemas.
- [x] Offline SQL, live upgrade, runtime CRUD, negative constraints, downgrade to the previous
  revision, re-upgrade and live metadata drift checks all pass on PostgreSQL 17.
- [x] No password hashing, auth endpoint, session/JWT behavior, seeded account or persistent
  production/development data is introduced.

**Files Created**:

- `apps/api/alembic/versions/0002_users_create_users_table.py`

**Files Modified**:

- `apps/api/alembic/env.py`
- `apps/api/tests/test_migrations.py`
- `apps/api/README.md`
- `.github/workflows/ci.yml`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- Generated the revision from SQLAlchemy metadata against a baseline-only acceptance database,
  then reviewed and hardened it with explicit enum lifecycle, grants, revocations and RLS policy.
- Kept Alembic as the sole migration history. No parallel Supabase CLI migration was introduced.
- The runtime policy intentionally permits all rows only to `vgu_buddy_runtime`; FastAPI will derive
  identity/role from verified application sessions in later tasks. Data API roles remain unable to
  reach the schema, table or enum.
- Did not force RLS on the table owner so the privileged Alembic connection can perform controlled
  migrations. The non-owner runtime role remains subject to the backend-only policy.
- Added schema-aware, allowlisted reflection. This fixed a real false-positive drift condition where
  Alembic recorded `0002_users` but `alembic check` could not see the non-default-schema table.

**Verification Results**:

- Focused migration/model/role suite — PASS, 20 tests.
- Full backend suite — PASS, 58 tests.
- `ruff check .` — PASS.
- `mypy app alembic tests` — PASS, strict mode over 25 source files.
- `python -m build` — PASS; isolated sdist and wheel build completed.
- Alembic `history` / `heads` — PASS; `0002_users` is the only head in a linear graph.
- Offline upgrade/downgrade SQL — PASS for enum/table/index creation, security statements and clean
  table/type removal.
- Docker Desktop 4.91.0 / Linux Engine 29.8.0 — PASS using `desktop-linux`.
- PostgreSQL 17.11 live upgrade — PASS; 10 columns, two enum labels, four named constraints and four
  physical indexes verified.
- Live security probe — PASS; RLS/policy verified, runtime CRUD and type usage succeeded, while
  `anon`, `authenticated` and `service_role` had no schema/table/type privileges.
- Live negative cases — PASS; unknown role and blank hash were rejected.
- Live downgrade/re-upgrade — PASS; downgrade removed only users/table enum objects and retained the
  baseline schema/runtime role; re-upgrade restored head and `alembic check` reported no drift.
- `pip-audit --strict -r requirements.lock` and `npm audit` — PASS, no known vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.

**Database Changes**: No persistent database was changed. Revision `0002_users` is ready to create
the private users table when deployed; all live acceptance changes occurred in a disposable Docker
database and were removed with its isolated volume.
**Environment Variables Added**: None.
**Business API Changes**: None.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-009 and does not
block unrelated authentication foundation work.
**Next Task**: `AUTH-010 — Create password hashing service (bcrypt)`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1312: | AUTH-009 | Create Alembic migration for users table — ✅ Completed | 1 | AUTH-008 | P0 |
- Legacy line 1321: | AUTH-017 | Create verified-current-user authentication dependency — ✅ Completed | 2 | AUTH-011, AUTH-009 | P0 |
- Legacy line 1359: | BE-010 | Create profile, catalog and photo migrations — ✅ Completed | 1 | BE-008, BE-009, AUTH-009, BE-004 | P0 |
- Legacy line 1385: | EVT-003 | Create Event, EventMedia and registration migrations — ✅ Completed | 1 | EVT-001, EVT-002, EVT-010, AUTH-009, BE-004 | P0 |
- Legacy line 1390: | EVT-008 | Create audit log model, migration and service — ✅ Completed | 2 | AUTH-009 | P0 |
- Legacy line 2647: creating the physical table ahead of AUTH-009.
- Legacy line 2693: - AUTH-009 remains responsible for reviewing and committing the generated enum/table migration,
- Legacy line 2724: **Next Task**: \`AUTH-009 — Create Alembic migration for users table\`.
- Legacy line 4263: Done: AUTH-009                Create Alembic migration for users table [P0; Phase 5; completed 2026-09-16]
- Legacy line 4537: **Dependencies:** AUTH-011, AUTH-009
- Legacy line 5205: Cx2; dependency AUTH-009 DONE, READY. It is not implemented here.
- Legacy line 5215: **Dependencies:** AUTH-009
- Legacy line 5343: Cx1; dependencies BE-008, BE-009, AUTH-009 and BE-004 DONE, READY. It is not implemented here.
- Legacy line 5352: **Dependencies:** BE-008, BE-009, AUTH-009, BE-004
- Legacy line 5946: Phase 10 / Cx1; dependencies EVT-001, EVT-002, EVT-010, AUTH-009 and BE-004 DONE, READY. It is not
- Legacy line 5956: **Dependencies:** EVT-001, EVT-002, EVT-010, AUTH-009, BE-004
