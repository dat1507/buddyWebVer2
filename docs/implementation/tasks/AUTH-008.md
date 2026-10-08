# AUTH-008

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-007

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2643-2725

### AUTH-008 — Create User database model with role field

**Status**: Completed (✅) on 2026-09-16
**Objective**: Define the backend-owned account model and its PostgreSQL metadata contract without
creating the physical table ahead of AUTH-009.

The registry supplied the task title, priority and AUTH-007 dependency but no dedicated task
contract. The operational acceptance criteria below align the ERD, private-schema boundary and
least-privilege authentication design.

**Operational Acceptance Criteria**:

- [x] `User` maps `app_private.users`, inherits the UUID/audit/soft-delete fields from `Base`, and is
  exported from `app.models`.
- [x] The model persists a required unique email and a required `password_hash`; it has no plaintext
  password column, relationship, response schema or logging behavior.
- [x] `role` uses the private native PostgreSQL `user_role` enum with exact `USER`/`ADMIN` labels,
  validates strings and defaults to least-privilege `USER` in both ORM and database writes.
- [x] `is_active` defaults to true, `email_verified` defaults to false, and nullable `last_login`
  uses a timezone-aware timestamp.
- [x] Blank email and password-hash values are rejected by named database constraints.
- [x] Role and active-state indexes are declared; the email unique constraint supplies the email
  index so a redundant second B-tree is not created.
- [x] Unit, strict typing, PostgreSQL DDL and isolated PostgreSQL 17 live checks pass, including
  defaults, negative cases and least-privilege runtime-role grants.
- [x] No Alembic revision, auth endpoint, password hashing, cookie/JWT logic, admin provisioning or
  persistent database change is introduced ahead of its owning task.

**Files Created**:

- `apps/api/tests/test_user_model.py`

**Files Modified**:

- `apps/api/app/models/user.py`
- `apps/api/app/models/__init__.py`
- `apps/api/README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- Used PostgreSQL `TEXT` for email and password hashes, avoiding storage-equivalent artificial
  `varchar(n)` limits; request-level length and email syntax validation remain owned by later auth
  schemas/services.
- Kept email uniqueness across soft deletion so an old account identity cannot be silently reused.
  AUTH-012 must trim and canonicalize email before persistence; the model does not mutate input.
- Declared ORM and server defaults together so SQLAlchemy inserts and direct/runtime-role inserts
  share the same least-privilege behavior.
- Kept `password_hash` as the only credential field. Sanitized API DTOs must continue to use an
  allowlist and never serialize the ORM object directly.
- AUTH-009 remains responsible for reviewing and committing the generated enum/table migration,
  including upgrade/downgrade behavior and production rollout considerations.

**Verification Results**:

- Focused User/UserRole suite — PASS, 14 tests.
- Full backend suite — PASS, 57 tests.
- `ruff check .` — PASS.
- `mypy app alembic tests` — PASS, strict mode over 24 source files.
- `python -m build` — PASS; isolated build contains the User model in both sdist and wheel.
- Alembic `history` / `heads` — PASS; no revision was added and the baseline remains the single
  head.
- Docker Desktop 4.91.0 / Linux Engine 29.8.0 — PASS using `desktop-linux`.
- Isolated PostgreSQL 17.11 live probe — PASS; native enum labels, four named constraints, role and
  active indexes, ORM/server defaults, invalid-role rejection and blank-email rejection verified.
- Runtime-role live insert — PASS with only `SELECT`, `INSERT`, `UPDATE`, `DELETE` table grants; the
  raw insert received `USER`, active and unverified defaults.
- Acceptance cleanup — PASS; the probe table/enum and isolated container, network and volume were
  removed, while the baseline migration remained intact until the disposable volume was removed.
- `pip-audit --strict -r requirements.lock` and `npm audit` — PASS, no known vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.

**Database Changes**: No persistent schema change. The disposable acceptance database received the
baseline migration and temporary metadata-created `app_private.users`/`user_role` objects; all
acceptance resources were removed afterward.
**Environment Variables Added**: None.
**Business API Changes**: None.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-008 and does not
block unrelated authentication foundation work.
**Next Task**: `AUTH-009 — Create Alembic migration for users table`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1311: | AUTH-008 | Create User database model with role field — ✅ Completed | 2 | AUTH-007 | P0 |
- Legacy line 1312: | AUTH-009 | Create Alembic migration for users table — ✅ Completed | 1 | AUTH-008 | P0 |
- Legacy line 1316: | AUTH-012 | Create auth service (register, login, verify role) — ✅ Completed | 3 | AUTH-008, AUTH-010, AUTH-011 | P0 |
- Legacy line 1323: | AUTH-019 | Create admin seed CLI command (\`python -m app.cli create-admin\`) — ✅ Completed | 2 | AUTH-008, AUTH-010 | P0 |
- Legacy line 1357: | BE-008 | Define unified StudentProfile and ProfilePhoto models — ✅ Completed | 2 | AUTH-008 | P0 |
- Legacy line 1383: | EVT-001 | Define Event editorial state, time and visibility model — ✅ Completed | 2 | BE-006, AUTH-008 | P0 |
- Legacy line 1401: | EVS-001 | Create EventSlider model, status enum, Pydantic schemas, and EN/DE field contract | 3 | BE-006, AUTH-008, EVT-001 | P0 |
- Legacy line 2470: The registry supplied the task title, priority and BE-003 dependency but no dedicated contract. The operational acceptance criteria below define the minimal shared behavior required by AUTH-008, EVT-001 and later persistence tasks.
- Legacy line 2583: behavior ahead of AUTH-008 and later tasks.
- Legacy line 2616: - Kept the enum in \`models/user.py\`, the planned home of the AUTH-008 User model, and re-exported it
- Legacy line 2641: **Next Task**: \`AUTH-008 — Create User database model with role field\`.
- Legacy line 2729: **Objective**: Persist the AUTH-008 User metadata through one reversible Alembic revision while
- Legacy line 2732: The registry supplied the task title, priority and AUTH-008 dependency but no dedicated task
- Legacy line 2739:   \`users\` table with all AUTH-008 columns, defaults, constraints and indexes.
- Legacy line 4262: Done: AUTH-008                Create User database model with role field [P0; Phase 5; completed 2026-09-16]
- Legacy line 5281: Phase 8 / Cx2; dependency AUTH-008 DONE, READY. It is not implemented here.
- Legacy line 5290: **Dependencies:** AUTH-008
- Legacy line 5851: Phase 10 / Cx2; dependencies BE-006 and AUTH-008 DONE, READY. It is not implemented here.
- Legacy line 5860: **Dependencies:** BE-006, AUTH-008
- Legacy line 6848: | EMAIL-001 (**Done 2026-09-24**) | Verification persistence + legacy migration | AUTH-008/009 | Legacy USER→NULL absent evidence; ADMIN access preserved; digest-only one-use 15m token persistence | Migration/model/Admin-regression/security tests |
- Legacy line 6905: - **Dependencies / ownership:** AUTH-008/009; Backend + Database.
- Legacy line 8152: This graph shows V2 tasks; already-existing prerequisite IDs such as AUTH-008/009, BE-012, FE-029, EVS-003 and ADMIN-005 remain mandatory exactly as listed in each task contract.
