# AUTH-017

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-011, AUTH-009

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3468-3552

### AUTH-017 — Create verified-current-user authentication dependency

**Status**: Completed (✅) on 2026-09-17
**Objective**: Give every future protected API a reusable server-authoritative identity boundary by
verifying the HttpOnly access cookie first, then loading the current active, non-deleted User and
role from PostgreSQL.

The task contract supplied the dependency boundary and two security acceptance criteria. The
operational criteria below make credential ordering, generic failures, client-identity rejection,
database-role authority and the boundary with AUTH-016/AUTH-018 explicit.

**Operational Acceptance Criteria**:

- [x] `require_access_claims` reads only the environment-specific access cookie and verifies the
  existing pinned JWT contract before the database dependency opens. Missing, malformed, expired,
  and refresh-token-in-access-cookie credentials share one no-store generic `401`.
- [x] `require_auth` queries the signed `sub` only and returns an active, non-deleted database User.
  A missing, inactive or soft-deleted account receives the same generic `401` without account-state
  disclosure.
- [x] Query parameters, request-body fields and UI state cannot select or replace current identity;
  only the verified access-token subject reaches the database predicate.
- [x] The signed role claim is not used for authorization. The returned User carries the current
  persisted role, so an old `ADMIN` claim cannot restore privileges after a database downgrade.
- [x] The dependency returns the ORM User for composition by future endpoints and role gates; it
  does not serialize password hashes, create a current-session endpoint, or add premature RBAC.
- [x] Focused security tests, full regression and disposable PostgreSQL 17 acceptance prove valid
  identity, client-identity rejection, stale-role downgrade, generic invalid-token/account failures,
  and runtime-role database access.

**Files Created**:

- `apps/api/app/api/dependencies.py`
- `apps/api/tests/test_auth_dependencies.py`

**Files Modified**:

- `apps/api/app/services/tokens.py`
- `apps/api/app/services/__init__.py`
- `apps/api/README.md`
- `README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- Access JWT verification is split from the database lookup so invalid credentials fail before a
  connection is requested. This keeps malformed public traffic outside the database pool.
- The JWT role remains a signed routing hint, not an authorization source. `require_auth` trusts the
  signed subject for lookup and the database User for current account state and role.
- Safe-route authentication does not require CSRF. State-changing endpoints must compose
  `require_auth` with the existing session-scoped CSRF dependency; AUTH-016 is a safe current-session
  read and AUTH-018 owns exact role enforcement.
- No product endpoint was added. This avoids implementing `/api/auth/me` early and preserves the
  established API/service boundaries while making the dependency ready for reuse.

**Verification Results**:

- Focused AUTH-017 dependency/security suite — PASS, 10 tests.
- Full backend suite — PASS, 244 tests.
- `ruff check .` and Ruff format checks for all AUTH-017 Python files — PASS.
- `mypy app alembic tests` — PASS, strict mode over 45 source files.
- Locked dependency consistency and `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel contain the dependency and tests.
- Alembic `history` / `heads` — PASS; existing `0003_refresh_sessions` remains the only head.
- Docker Linux Engine 29.8.0 / Compose 5.5.1 — PASS on `desktop-linux`.
- Disposable PostgreSQL 17 live acceptance — PASS: healthy isolated container, migrations at
  `0003`, runtime database health, signed-subject identity, DB-authoritative role downgrade,
  inactive/deleted denial, generic anonymous denial, and `alembic check` with no schema drift.
  Its isolated container, network and volume were removed afterward.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern and AUTH-017 temporary-file/resource scans — PASS.

**Database Changes**: None; AUTH-017 reads the existing `app_private.users` table. Live acceptance
used and removed an isolated Compose volume.
**Environment Variables Added**: None; existing `DATABASE_URL`, `AUTH_JWT_SECRET` and
`AUTH_COOKIE_SECURE` contracts are reused.
**Business API Changes**: None; added reusable `require_access_claims` and `require_auth`
dependencies for later protected endpoints.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-017 and does not
block unrelated authentication core work.
**Next Task**: `AUTH-016 — Create sanitized current-session endpoint`.


### Legacy lines 4532-4546

### AUTH-017 — Create verified-current-user authentication dependency

**Task ID:** `AUTH-017`
**Change:** Updated existing; **Status:** Completed (✅) on 2026-09-17; **Priority:** P0; **Phase:** 5
**Goal:** Give profile/media/matching endpoints a current server identity.
**Dependencies:** AUTH-011, AUTH-009
**Scope:** Verify access-cookie JWT and load active, non-deleted User; role is checked against the database.

**Acceptance Criteria:**

- [x] Invalid/expired/missing cookie or deleted/inactive user is rejected; stale JWT role cannot restore removed privileges.
- [x] Current identity is never supplied by a body, query string or UI store.

**Out of Scope:** Replacing the completed auth transport design.


## Cross-reference occurrences outside extracted headings

- Legacy line 1320: | AUTH-016 | Create sanitized current-session endpoint — ✅ Completed | 1 | AUTH-017 | P0 |
- Legacy line 1321: | AUTH-017 | Create verified-current-user authentication dependency — ✅ Completed | 2 | AUTH-011, AUTH-009 | P0 |
- Legacy line 1322: | AUTH-018 | Create \`require_role(role)\` FastAPI dependency (verify role) — ✅ Completed | 2 | AUTH-017 | P0 |
- Legacy line 1328: | AUTH-024 | Implement session logout endpoint — Backend/live and frontend/cache acceptance PASS | 2 | AUTH-015, AUTH-017, AUTH-011A | P0 |
- Legacy line 1361: | BE-012 | Create own-profile read/update endpoints — ✅ Completed | 2 | BE-011, AUTH-017, AUTH-011A | P0 |
- Legacy line 1387: | EVT-005 | Create audience-safe event list, detail and calendar queries | 2 | EVT-004, AUTH-017 | P0 |
- Legacy line 1389: | EVT-007 | Create \`POST /api/events/:id/register\` (user registers for event) | 2 | EVT-002, AUTH-017 | P1 |
- Legacy line 1464: | MATCH-009 | Create own-match result endpoint | 2 | MATCH-014, AUTH-017 | P0 |
- Legacy line 1466: | MATCH-011 | Create \`POST /api/matching/feedback\` (user feedback) | 2 | MATCH-002, AUTH-017 | P1 |
- Legacy line 2955:   changes are reflected when AUTH-015 issues a new access token; AUTH-017 must still reload active,
- Legacy line 3321:   APIs independently reload authorization state through AUTH-017/AUTH-018.
- Legacy line 3428:   the replacement access token. AUTH-017 will still reload User state on protected requests rather
- Legacy line 3466: **Next Task**: \`AUTH-017 — Create verified-current-user authentication dependency\`.
- Legacy line 3573: - [x] Missing, malformed, expired and wrong-token-type access cookies retain AUTH-017's same generic
- Legacy line 3607: - Focused AUTH-016 endpoint/security/OpenAPI suite — PASS, 8 tests; combined AUTH-016/AUTH-017
- Legacy line 3626: **Database Changes**: None; AUTH-016 reads the existing \`app_private.users\` table through AUTH-017.
- Legacy line 3708: through AUTH-017. Live acceptance used and removed an isolated Compose volume.
- Legacy line 3859: - **Access-token limitation:** existing AUTH-017 does not consult refresh-family revocation. A
- Legacy line 4271: Done: AUTH-017                Create verified-current-user authentication dependency [P0; Phase 5; completed 2026-09-17]
- Legacy line 4552: **Dependencies:** AUTH-017
- Legacy line 4839: **Dependencies:** AUTH-015, AUTH-017, AUTH-011A
- Legacy line 4889: skew remains AUTH-017's contract. AUTH-020 production Redis/TLS/ingress acceptance and legacy Gemini
- Legacy line 5411: dependencies BE-011, AUTH-017 and AUTH-011A DONE, READY. It is not implemented here.
- Legacy line 5420: **Dependencies:** BE-011, AUTH-017, AUTH-011A
- Legacy line 6009: P0 / Phase 10 / Cx2; dependencies EVT-004 and AUTH-017 DONE, READY. It is not implemented here.
- Legacy line 6018: **Dependencies:** EVT-004, AUTH-017
- Legacy line 6372: **Dependencies:** MATCH-014, AUTH-017
- Legacy line 8547: - **Dependencies:** \`EVT-004\`, \`EVT-010\`, \`EVS-003\`, \`AUTH-017\` and migration \`0007\` DONE.
