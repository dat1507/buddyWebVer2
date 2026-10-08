# AUTH-014

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-012, AUTH-011A

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3269-3359

### AUTH-014 — Create CSRF-protected `POST /api/auth/login` endpoint

**Status**: Completed (✅) on 2026-09-17
**Objective**: Expose the AUTH-012 credential service through the shared public login endpoint,
establish cookie-only JWT credentials, rotate pre-auth CSRF evidence into a session-bound context,
and return only the sanitized database identity required for later frontend role routing.

The registry supplied the task title, dependencies and AUTH-ARCH-001 transport contract. The
operational criteria below make failure uniformity, transaction ordering, cookie/CSRF rotation and
the boundary with AUTH-015 explicit.

**Operational Acceptance Criteria**:

- [x] `POST /api/auth/login` accepts only strict string `email` and `password` fields and requires
  the signed pre-auth CSRF cookie/header pair plus an exact trusted Origin/Referer. Invalid CSRF is
  rejected with the generic `403` before the database dependency opens.
- [x] The endpoint never accepts a requested role or login-page identity. It authenticates the
  canonical email and returns the actual persisted `USER`/`ADMIN` role.
- [x] Unknown email, malformed email, wrong/empty/overlong password, inactive account and
  soft-deleted account return the same no-store `401 Invalid email or password.` without reflecting
  submitted values or setting auth cookies.
- [x] Successful login stages a timezone-aware `last_login`, creates a fresh access/refresh JWT
  pair, commits the database transaction, then sets both credentials only as hardened HttpOnly
  cookies. Neither JWT, the password nor its hash appears in JSON or object representations.
- [x] The response returns only a sanitized User DTO (`id`, canonical `email`, persisted `role`,
  `email_verified`) plus the readable session CSRF token. The matching CSRF cookie replaces the
  pre-auth token and is HMAC-bound to the JWT session identifier.
- [x] Token/CSRF configuration failures fail closed with a sanitized no-store `503`; unexpected
  database/commit failures roll back and expose neither internal diagnostics nor partial cookies.
- [x] AUTH-014 introduces no client token storage, role trust, database migration or claim of
  refresh replay protection. Persisted refresh-session rotation/reuse detection remains AUTH-015.
- [x] Focused API/security tests, full regression and disposable PostgreSQL 17 live acceptance
  prove successful login, real `last_login` persistence, wrong-password and missing-user denial.

**Files Created**:

- `apps/api/tests/test_auth_login_api.py`

**Files Modified**:

- `apps/api/app/api/auth.py`
- `apps/api/app/main.py`
- `apps/api/app/schemas/auth.py`
- `apps/api/app/schemas/__init__.py`
- `apps/api/README.md`
- `README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- Both `/login` and `/adminLogin` must later call this one endpoint. The backend does not accept an
  expected role; AUTH-022/AUTH-023 route from the returned persisted role, while future protected
  APIs independently reload authorization state through AUTH-017/AUTH-018.
- Auth and session-CSRF credentials are prepared before commit but attached to the response only
  after commit succeeds. This prevents a failed database transaction from returning a usable
  partial cookie session.
- Login rotates the readable/cookie CSRF pair into `session` scope using the token pair's fresh
  `sid`. AUTH-015 remains responsible for persisting and atomically consuming refresh `jti` state;
  AUTH-024 later revokes that state and clears all cookies.
- Login credentials intentionally use generic authentication failure rather than request-level
  email/password policy disclosure. Registration and future password change retain ownership of
  password-strength validation.

**Verification Results**:

- Focused login endpoint/security suite — PASS, 19 tests.
- Full backend suite — PASS, 201 tests.
- `ruff check .` — PASS; changed Python files pass Ruff formatting.
- `mypy app alembic tests` — PASS, strict mode over 37 source files.
- Locked dependency consistency and backend package build — PASS.
- Alembic `history` / `heads` — PASS; `0002_users` remains the only head.
- Disposable PostgreSQL 17 Compose acceptance — PASS: healthy container, migrations at
  `0002_users`, real registration/login through the runtime role, persisted `last_login`, actual
  `USER` role, generic wrong-password/missing-user `401`, and complete isolated resource cleanup.
- Backend runtime dependency audit — PASS, no known vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Frontend production dependency audit — PASS, no known vulnerabilities.

**Database Changes**: None; AUTH-014 uses the existing `app_private.users` schema and does not yet
create persisted refresh-session state. The live test database and its isolated volume were
removed after acceptance.
**Environment Variables Added**: None; the existing `AUTH_JWT_SECRET`, `AUTH_CSRF_SECRET`,
`AUTH_COOKIE_SECURE`, `CORS_ALLOWED_ORIGINS` and `DATABASE_URL` contracts are reused.
**Business API Changes**: Added `POST /api/auth/login`, protected by pre-auth CSRF and exact source
origin validation; success returns a sanitized User/session-CSRF payload and cookie-only JWTs.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-014 and does not
block unrelated authentication core work.
**Next Task**: `AUTH-015 — Create CSRF-protected POST /api/auth/refresh endpoint with rotation/reuse detection`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1318: | AUTH-014 | Create CSRF-protected \`POST /api/auth/login\` endpoint (sets cookies; returns sanitized user) — ✅ Completed | 2 | AUTH-012, AUTH-011A | P0 |
- Legacy line 1325: | AUTH-021 | Connect session client, registration, and auth bootstrap — ✅ Completed | 2 | AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024 | P0 |
- Legacy line 3049:   AUTH-014/AUTH-015/AUTH-024.
- Legacy line 3085: the AUTH-013/AUTH-014 HTTP endpoints or refresh-session persistence.
- Legacy line 3115:   state. AUTH-013/AUTH-014 and later AUTH-015 retain ownership of the request transaction so account,
- Legacy line 3168: **Business API Changes**: None; AUTH-013/AUTH-014 own the public register/login routes.
- Legacy line 3224: - The endpoint deliberately does not log a user in. AUTH-014 owns login and AUTH-015 owns persisted
- Legacy line 3267: **Next Task**: \`AUTH-014 — Create CSRF-protected POST /api/auth/login endpoint (sets cookies; returns sanitized user)\`.
- Legacy line 4269: Done: AUTH-014                Create CSRF-protected \`POST /api/auth/login\` endpoint (sets cookies; returns sanitized user) [P0; Phase 5; completed 2026-09-17]
- Legacy line 4862: **Dependencies:** AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024
