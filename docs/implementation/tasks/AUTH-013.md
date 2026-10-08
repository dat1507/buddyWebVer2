# AUTH-013

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-012, AUTH-011A

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3174-3268

### AUTH-013 — Create CSRF-protected `POST /api/auth/register` endpoint (role=USER always)

**Status**: Completed (✅) on 2026-09-17
**Objective**: Expose the AUTH-012 registration service through a narrow public HTTP boundary that
requires pre-auth CSRF evidence, accepts explicit consent, always creates role `USER`, owns the
request transaction, and returns no authentication or account material.

The registry supplied only the task title and dependencies. The operational criteria below make
the request schema, password boundary, validation disclosure, transaction, and response behavior
explicit for frontend integration in AUTH-021.

**Operational Acceptance Criteria**:

- [x] `POST /api/auth/register` requires the signed pre-auth CSRF cookie/header pair and exact
  trusted source origin. Every invalid, mismatched, missing, wrong-scope or wrong-origin condition
  returns the same generic `403` before the database dependency is opened.
- [x] The strict request schema accepts only `email`, `password`, and JSON boolean `consent: true`;
  missing/false/string consent and extra fields such as `role` fail validation before mutation.
- [x] Email uses the shared canonical identity contract. Passwords require at least 8 characters,
  permit Unicode/whitespace without trimming or normalization, and reject values over bcrypt's
  72-byte UTF-8 limit rather than truncating them.
- [x] Validation responses retain field/type/message diagnostics but omit raw `input` and validator
  context, preventing rejected passwords and other submitted values from being reflected. Password
  is also excluded from the Pydantic request representation.
- [x] The endpoint delegates hashing and least-privilege construction to AUTH-012, commits only
  after a successful flush, and rolls back unexpected commit failures. Client input cannot choose
  a role; persisted accounts are active, unverified `USER` records.
- [x] Success returns only `201 {"status":"registered"}` with no user identifiers, password/hash,
  JWT, access/refresh cookie, or authenticated session. Responses are `no-store`/`no-cache`.
- [x] PostgreSQL unique-email conflicts return generic `409 Account registration failed.` without
  reflecting the canonical address; unexpected infrastructure failures remain generic `500`s.
- [x] Focused security tests, full regression, and disposable PostgreSQL 17 runtime-role acceptance
  prove real health, persistence, duplicate conflict, cleanup, and migration round-trip behavior.

**Files Created**:

- `apps/api/tests/test_auth_registration_api.py`

**Files Modified**:

- `apps/api/app/api/auth.py`
- `apps/api/app/main.py`
- `apps/api/app/schemas/auth.py`
- `apps/api/app/schemas/__init__.py`
- `apps/api/README.md`
- `README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- The endpoint deliberately does not log a user in. AUTH-014 owns login and AUTH-015 owns persisted
  refresh-session rotation/reuse detection; issuing partial session state during registration would
  cross those transaction and security boundaries.
- Public STUDENT registration uses the confirmed 8-character product minimum. The existing bcrypt
  architecture retains the stricter technical ceiling of 72 UTF-8 bytes; all character classes,
  including Unicode and whitespace, otherwise remain allowed without composition rules. The ADMIN
  provisioning policy remains a separate 15-character minimum.
- The mandatory consent boolean is a registration gate, not a claimed legal audit ledger. Durable
  consent version/time/source evidence requires a dedicated product contract and migration if the
  applicable privacy policy later requires it.
- Request-validation sanitization is application-wide so future secret-bearing endpoints cannot
  accidentally inherit FastAPI's raw invalid-input reflection. The response keeps the established
  `detail` envelope and non-sensitive error location/message/type fields.

**Verification Results**:

- Focused registration endpoint/security suite — PASS, 20 tests.
- Full backend suite — PASS, 182 tests.
- `ruff check app alembic tests` — PASS.
- `mypy app alembic tests` — PASS, strict mode over 36 source files.
- Locked development environment synchronization and `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel include the endpoint, schemas and tests.
- Docker Desktop 4.91.0 / Linux Engine 29.8.0 — PASS on `desktop-linux` after moving only stale
  AF_UNIX runtime-socket directories to recoverable AUTH-013 backups; no image, existing volume or
  development database was removed.
- Disposable PostgreSQL 17 Compose acceptance — PASS: healthy container, Alembic at `0002_users`,
  least-privilege API database health `200`, real registration/persisted `USER`, duplicate `409`,
  test-row cleanup, and downgrade/base/re-upgrade/head. Its isolated container, network and volume
  were removed afterward.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern repository scan — PASS, no credential-shaped matches.

**Database Changes**: None; AUTH-013 uses the existing `app_private.users` schema. Live acceptance
inserted and removed one disposable account before deleting its project-specific test volume.
**Environment Variables Added**: None.
**Business API Changes**: Added public state-changing `POST /api/auth/register`, protected by the
existing pre-auth CSRF contract; it never creates an authenticated session.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-013 and does not
block unrelated authentication core work.
**Next Task**: `AUTH-014 — Create CSRF-protected POST /api/auth/login endpoint (sets cookies; returns sanitized user)`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1317: | AUTH-013 | Create CSRF-protected \`POST /api/auth/register\` endpoint (role=USER always) — ✅ Completed | 2 | AUTH-012, AUTH-011A | P0 |
- Legacy line 1325: | AUTH-021 | Connect session client, registration, and auth bootstrap — ✅ Completed | 2 | AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024 | P0 |
- Legacy line 3085: the AUTH-013/AUTH-014 HTTP endpoints or refresh-session persistence.
- Legacy line 3115:   state. AUTH-013/AUTH-014 and later AUTH-015 retain ownership of the request transaction so account,
- Legacy line 3168: **Business API Changes**: None; AUTH-013/AUTH-014 own the public register/login routes.
- Legacy line 3172: **Next Task**: \`AUTH-013 — Create CSRF-protected POST /api/auth/register endpoint (role=USER always)\`.
- Legacy line 4268: Done: AUTH-013                Create CSRF-protected \`POST /api/auth/register\` endpoint (role=USER always) [P0; Phase 5; completed 2026-09-17]
- Legacy line 4397: The final acceptance is a gate, not a new implementation task: create one Admin through AUTH-019, register one Vietnamese and one international USER through AUTH-013/AUTH-021, complete both profiles through the existing Profile flow, run/preview/publish through the new Admin UI, accept from both user sessions, and verify the active Buddy result after reload. It must use PostgreSQL and the configured private storage service; no fake users, fake match result or frontend-only success state may satisfy it.
- Legacy line 4767: **Dependencies:** BE-001; current AUTH-013/014/015/016 identity and transaction contracts.
- Legacy line 4862: **Dependencies:** AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024
