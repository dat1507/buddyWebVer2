# AUTH-015

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-011, AUTH-011A

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3360-3467

### AUTH-015 — Create CSRF-protected `POST /api/auth/refresh` endpoint with rotation/reuse detection

**Status**: Completed (✅) on 2026-09-17
**Objective**: Make refresh credentials one-use and server-authoritative by persisting each session
family's current refresh identifier, rotating it atomically, and revoking the family when an older
valid token is presented again.

The registry supplied the task title, dependencies and AUTH-ARCH-001 cookie transport contract. The
operational criteria below make transaction ownership, concurrency, authoritative role reload,
generic failure behavior and the boundary with logout explicit.

**Operational Acceptance Criteria**:

- [x] Login persists one `app_private.refresh_sessions` row in the same transaction as `last_login`.
  The row uses JWT `sid` as its family ID and stores the owning User, current refresh `jti`, expiry,
  and nullable revocation timestamp; no raw token is persisted.
- [x] `POST /api/auth/refresh` accepts no body and reads only the environment-specific HttpOnly
  refresh cookie. It verifies the refresh JWT before opening the database dependency, then requires
  a matching session-scoped CSRF cookie/header and exact trusted Origin/Referer.
- [x] Rotation row-locks the session family, accepts only its current `jti`, reloads the active,
  non-deleted User and current database role, and atomically replaces the `jti` and expiry while
  preserving the `sid`.
- [x] Presenting an older valid refresh token is reuse: the endpoint commits `revoked_at` for the
  entire family and returns the same no-store generic `401` as missing, malformed, expired,
  already-revoked, wrong-user, inactive-user and deleted-user session failures.
- [x] Successful rotation commits before setting a fresh 15-minute access cookie, seven-day refresh
  cookie, and new HMAC session-bound CSRF context. JSON contains only the sanitized current User and
  readable CSRF value; no JWT or password material is exposed.
- [x] Commit failures roll back and set no replacement cookies. Duplicate concurrent refreshes are
  intentionally not both accepted: clients must single-flight refresh, which remains AUTH-021.
- [x] Alembic revision `0003_refresh_sessions` creates the foreign key, unique current-`jti`
  constraint and lookup indexes, revokes `PUBLIC`/Data API access, and grants only the backend
  runtime role through RLS. Upgrade/downgrade/re-upgrade succeeds on PostgreSQL 17.
- [x] Focused unit/API/migration tests, full regression and disposable live PostgreSQL acceptance
  prove initial persistence, successful rotation, role refresh, old-token reuse revocation, and
  rejection of the newest token after family revocation.

**Files Created**:

- `apps/api/alembic/versions/0003_refresh_sessions.py`
- `apps/api/app/models/refresh_session.py`
- `apps/api/app/services/refresh_sessions.py`
- `apps/api/tests/test_auth_refresh_api.py`
- `apps/api/tests/test_refresh_session_model.py`
- `apps/api/tests/test_refresh_sessions.py`

**Files Modified**:

- `apps/api/app/api/auth.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/schemas/auth.py`
- `apps/api/app/schemas/__init__.py`
- `apps/api/app/services/tokens.py`
- `apps/api/app/services/__init__.py`
- `apps/api/tests/test_auth_login_api.py`
- `apps/api/tests/test_migrations.py`
- `apps/api/README.md`
- `README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- The database row is the replay authority; JWT signature validity alone does not prove freshness.
  `SELECT ... FOR UPDATE` serializes one family so a consumed `jti` cannot be rotated twice.
- Reuse revocation is deliberately committed rather than rolled back with the `401`. Once reuse is
  detected, every token in that family remains invalid, including a newer token already returned by
  a concurrent request.
- Refresh tokens omit role. Rotation reloads the User under lock and supplies the persisted role to
  the replacement access token. AUTH-017 will still reload User state on protected requests rather
  than treating that access claim as final authorization.
- Failed refresh does not claim logout or clear cookies. AUTH-024 owns explicit family revocation
  and matching cookie clearing; AUTH-021 owns frontend single-flight and private-cache handling.

**Verification Results**:

- Focused login/refresh/model/service/migration suite — PASS, 58 tests.
- Full backend suite — PASS, 234 tests.
- `ruff check .` and Ruff format checks for all AUTH-015 Python files — PASS. The repository-wide
  format-only check still reports seven historical out-of-scope files; none was modified.
- `mypy app alembic tests` — PASS, strict mode over 43 source files.
- Locked dependency consistency and `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel contain the refresh model, service,
  endpoint and tests.
- Alembic `history` / `heads` — PASS; `0003_refresh_sessions` is the only head in a linear graph.
- Docker Desktop 4.91.0 / Linux Engine 29.8.0 / Compose 5.5.1 — PASS on `desktop-linux`; current
  Compose configuration validates successfully.
- Disposable PostgreSQL 17 live acceptance — PASS: healthy container, upgrade to `0003`, runtime
  connection, login family persistence, successful rotation with the same `sid` and new `jti`/CSRF,
  old-token reuse `401` with persisted revocation, newest-token rejection, downgrade to `0002`,
  re-upgrade to head, and complete isolated container/network/volume cleanup.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern and AUTH-015 temporary-file scans — PASS.

**Database Changes**: Added Alembic revision `0003_refresh_sessions` and the backend-only
`app_private.refresh_sessions` table. No persistent development database was changed; live checks
used and removed an isolated Compose volume.
**Environment Variables Added**: None; existing database, JWT, CSRF, cookie and CORS contracts are
reused.
**Business API Changes**: Added CSRF-protected `POST /api/auth/refresh`; success returns a sanitized
User/session-CSRF payload and rotates cookie-only JWTs.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-015 and does not
block unrelated authentication core work.
**Next Task**: `AUTH-017 — Create verified-current-user authentication dependency`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1319: | AUTH-015 | Create CSRF-protected \`POST /api/auth/refresh\` endpoint with rotation/reuse detection — ✅ Completed | 2 | AUTH-011, AUTH-011A | P0 |
- Legacy line 1325: | AUTH-021 | Connect session client, registration, and auth bootstrap — ✅ Completed | 2 | AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024 | P0 |
- Legacy line 1328: | AUTH-024 | Implement session logout endpoint — Backend/live and frontend/cache acceptance PASS | 2 | AUTH-015, AUTH-017, AUTH-011A | P0 |
- Legacy line 2926: - [x] Rotation does not claim stateless replay protection. AUTH-015 must atomically compare/consume
- Legacy line 2955:   changes are reflected when AUTH-015 issues a new access token; AUTH-017 must still reload active,
- Legacy line 2979: AUTH-015.
- Legacy line 3049:   AUTH-014/AUTH-015/AUTH-024.
- Legacy line 3115:   state. AUTH-013/AUTH-014 and later AUTH-015 retain ownership of the request transaction so account,
- Legacy line 3224: - The endpoint deliberately does not log a user in. AUTH-014 owns login and AUTH-015 owns persisted
- Legacy line 3278: the boundary with AUTH-015 explicit.
- Legacy line 3299:   refresh replay protection. Persisted refresh-session rotation/reuse detection remains AUTH-015.
- Legacy line 3326:   \`sid\`. AUTH-015 remains responsible for persisting and atomically consuming refresh \`jti\` state;
- Legacy line 3358: **Next Task**: \`AUTH-015 — Create CSRF-protected POST /api/auth/refresh endpoint with rotation/reuse detection\`.
- Legacy line 4270: Done: AUTH-015                Create CSRF-protected \`POST /api/auth/refresh\` endpoint with rotation/reuse detection [P0; Phase 5; completed 2026-09-17]
- Legacy line 4839: **Dependencies:** AUTH-015, AUTH-017, AUTH-011A
- Legacy line 4862: **Dependencies:** AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024
