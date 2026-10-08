# AUTH-016

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-017

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3553-3635

### AUTH-016 — Create sanitized current-session endpoint

**Status**: Completed (✅) on 2026-09-17
**Objective**: Expose one safe session-bootstrap read that restores the current server-verified User
after a browser reload without exposing credentials, account internals, or profile state.

The task contract supplied the endpoint, dependency and DTO boundary. The operational criteria
below make caching, mutation, CSRF, role freshness, profile independence and response minimization
explicit.

**Operational Acceptance Criteria**:

- [x] `GET /api/auth/me` composes the completed `require_auth` dependency and accepts no body,
  query-selected identity, bearer token, role input or frontend session assertion.
- [x] Success returns exactly the existing sanitized User DTO: `id`, canonical `email`, current
  persisted `role`, and `email_verified`. JWTs, password/hash, `sid`/`jti`, refresh/CSRF state,
  audit fields and profile data are absent.
- [x] Every successful response sets `Cache-Control: no-store` and `Pragma: no-cache`; the endpoint
  does not set or rotate cookies, flush, commit, roll back, or otherwise mutate session/database
  state.
- [x] Missing, malformed, expired and wrong-token-type access cookies retain AUTH-017's same generic
  no-store `401 Authentication required.` behavior; invalid credentials fail before a database
  connection is requested.
- [x] The response reflects the current database role even when the signed access-token role is
  stale. Anonymous and inactive accounts are rejected during live acceptance.
- [x] Authentication depends only on the User row. No StudentProfile lookup or onboarding-readiness
  requirement is introduced; FE-038 and the profile APIs retain that separate responsibility.
- [x] Focused API/OpenAPI tests, full regression and disposable PostgreSQL 17 live acceptance prove
  the minimized response, role freshness, no-store behavior and generic unauthenticated response.

**Files Created**:

- `apps/api/tests/test_auth_me_api.py`

**Files Modified**:

- `apps/api/app/api/auth.py`
- `apps/api/README.md`
- `README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- The existing `SanitizedUserResponse` is reused so login, refresh and reload share one identity
  shape instead of introducing a divergent session DTO.
- `/me` is a safe GET and therefore does not require CSRF. It performs no session rotation; expired
  access recovery remains the frontend single-flight refresh flow in AUTH-021.
- Profile absence is not an authentication failure. The endpoint intentionally cannot infer
  onboarding completeness or matching eligibility from an account-only read.
- The skill-guided change preserves the completed auth dependency and token logic; AUTH-016 adds
  only the smallest route adapter and security-focused contract tests.

**Verification Results**:

- Focused AUTH-016 endpoint/security/OpenAPI suite — PASS, 8 tests; combined AUTH-016/AUTH-017
  focused suite — PASS, 18 tests.
- Full backend suite — PASS, 252 tests.
- `ruff check .` and Ruff format checks for all AUTH-016 Python files — PASS.
- `mypy app alembic tests` — PASS, strict mode over 46 source files.
- Locked dependency consistency and `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel contain the endpoint and tests.
- Alembic `history` / `heads` — PASS; existing `0003_refresh_sessions` remains the only head.
- Docker Linux Engine 29.8.0 / Compose 5.5.1 — PASS on `desktop-linux`.
- Disposable PostgreSQL 17 live acceptance — PASS: healthy isolated container, migrations at
  `0003`, API database health `200`, exact sanitized ADMIN response, current USER role after a live
  downgrade with the same token, no cookie mutation, inactive/anonymous `401`, and `alembic check`
  with no schema drift. Its isolated container, network and volume were removed afterward.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern and AUTH-016 temporary-file/resource scans — PASS.

**Database Changes**: None; AUTH-016 reads the existing `app_private.users` table through AUTH-017.
Live acceptance used and removed an isolated Compose volume.
**Environment Variables Added**: None.
**Business API Changes**: Added authenticated, no-store `GET /api/auth/me` returning only the
sanitized current User DTO.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-016 and does not
block unrelated authentication core work.
**Next Task**: `AUTH-018 — Create require_role(role) FastAPI dependency (verify role)`.


### Legacy lines 4547-4561

### AUTH-016 — Create sanitized current-session endpoint

**Task ID:** `AUTH-016`
**Change:** Updated existing; **Status:** Completed (✅) on 2026-09-17; **Priority:** P0; **Phase:** 5
**Goal:** Restore a verified session before profile routing.
**Dependencies:** AUTH-017
**Scope:** GET /api/auth/me through require_auth with no-store and sanitized User DTO.

**Acceptance Criteria:**

- [x] Reload returns verified current role without tokens/password hash; unauthenticated request returns 401.
- [x] Profile absence does not prevent authentication; onboarding readiness is fetched separately by FE-038.

**Out of Scope:** Returning whole profile or modifying AUTH-ARCH-001.


## Cross-reference occurrences outside extracted headings

- Legacy line 1320: | AUTH-016 | Create sanitized current-session endpoint — ✅ Completed | 1 | AUTH-017 | P0 |
- Legacy line 1325: | AUTH-021 | Connect session client, registration, and auth bootstrap — ✅ Completed | 2 | AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024 | P0 |
- Legacy line 3477: database-role authority and the boundary with AUTH-016/AUTH-018 explicit.
- Legacy line 3517:   \`require_auth\` with the existing session-scoped CSRF dependency; AUTH-016 is a safe current-session
- Legacy line 3551: **Next Task**: \`AUTH-016 — Create sanitized current-session endpoint\`.
- Legacy line 4272: Done: AUTH-016                Create sanitized current-session endpoint [P0; Phase 5; completed 2026-09-17]
- Legacy line 4862: **Dependencies:** AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024
