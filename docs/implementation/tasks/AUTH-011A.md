# AUTH-011A

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** BE-001, AUTH-ARCH-001

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2987-3079

### AUTH-011A — Create signed CSRF service and `GET /api/auth/csrf` endpoint

**Status**: Completed (✅) on 2026-09-16
**Objective**: Establish the signed double-submit CSRF boundary before any auth or domain mutation
endpoint is introduced, including an independently testable pre-auth bootstrap and primitives for
refresh-session-bound authenticated requests.

**Operational Acceptance Criteria**:

- [x] `GET /api/auth/csrf` returns a fresh one-hour pre-auth token in a sanitized JSON schema and
  sets the identical signed value in an HttpOnly, host-only cookie; responses are `no-store` and
  `no-cache`.
- [x] Tokens use HMAC-SHA256 with a dedicated URL-safe-base64 `AUTH_CSRF_SECRET` that decodes to at
  least 32 bytes. The secret is lazy-loaded, server-only, redacted, independently generated from
  the JWT secret, and never exposed to the frontend.
- [x] The signed canonical payload has an explicit version, scope, 256-bit nonce, issue/expiry time
  and binding tag. Verification checks the signature in constant time, exact key set, exact scope,
  exact lifetime, clock skew, nonce length and sanitized failure behavior.
- [x] Pre-auth and authenticated CSRF tokens are not interchangeable. Authenticated tokens are
  HMAC-bound to one refresh-session UUID and expire with that seven-day session; the session UUID is
  not exposed in the token payload.
- [x] Unsafe requests require exactly one `X-CSRF-Token`, the matching cookie, a valid signed token,
  and one exact allowlisted `Origin`; the origin portion of `Referer` is accepted only when Origin
  is absent. Missing, duplicate, suffix-confused, `null`, non-ASCII and malformed evidence fails
  closed with one generic error.
- [x] Production uses `__Host-vgu_buddy_csrf` with `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`,
  no `Domain`, and fixed expiry. Explicit local HTTP mode uses the distinct
  `vgu_buddy_csrf_dev` name and omits only `Secure`; clearing preserves matching attributes.
- [x] Direct construction of CSRF settings still rejects weak keys, empty origin sets, wildcards,
  paths and other unsafe origin syntax; the endpoint returns a sanitized 503 if its secret is
  absent or invalid.
- [x] The readable token is returned only by the bootstrap response for in-memory frontend use; no
  localStorage/sessionStorage contract, auth endpoint, user mutation, database table or migration
  is introduced by this task.

**Files Created**:

- `apps/api/app/api/auth.py`
- `apps/api/app/schemas/auth.py`
- `apps/api/app/services/csrf.py`
- `apps/api/tests/test_csrf.py`

**Files Modified**:

- `apps/api/app/core/config.py`
- `apps/api/app/main.py`
- `apps/api/app/schemas/__init__.py`
- `apps/api/app/services/__init__.py`
- `apps/api/.env.example`
- `apps/api/README.md`
- `README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- Used a compact versioned HMAC token instead of another JWT so CSRF evidence cannot be confused
  with access/refresh credentials. All untrusted-token failures collapse to
  `CSRF validation failed.` without reflecting token material.
- The cookie is HttpOnly even though this is double-submit: the bootstrap endpoint returns the same
  value in JSON for memory-only use, so frontend JavaScript never needs `document.cookie` access.
- The HMAC binding contains the refresh-session UUID only for authenticated scope. Login/refresh
  tasks must rotate to that scope, and logout must clear the cookie; those stateful flows remain in
  AUTH-014/AUTH-015/AUTH-024.
- Exact source-origin validation complements signed double-submit and `SameSite=Lax`; CORS and
  SameSite remain defense in depth rather than substitutes for request validation.

**Verification Results**:

- Focused CSRF/config/origin/cookie/endpoint suite — PASS, 29 tests.
- Full backend suite — PASS, 126 tests.
- `ruff check .` — PASS; Ruff format check — PASS on all eight changed Python files.
- `mypy app alembic tests` — PASS, strict mode over 33 source files.
- Python 3.12.10 clean locked dependency install and `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel include the CSRF service, schema, route,
  and tests.
- Alembic `history` / `heads` — PASS; `0002_users` remains the only head.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern scan of tracked source/config files — PASS, no credential-shaped matches.

**Database Changes**: None; AUTH-011A is a stateless cryptographic/request-boundary task and did not
require Docker or a live database acceptance run.
**Environment Variables Added**: `AUTH_CSRF_SECRET`; existing `AUTH_COOKIE_SECURE` and
`CORS_ALLOWED_ORIGINS` are reused for the matching cookie and exact source-origin policies.
**Business API Changes**: Added public safe bootstrap `GET /api/auth/csrf`; no state-changing or
authenticated business endpoint was added.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-011A and does not
block unrelated authentication foundation work.
**Next Task**: `AUTH-012 — Create auth service (register, login, verify role)`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1315: | AUTH-011A | Create signed CSRF service and \`GET /api/auth/csrf\` endpoint — ✅ Completed | 2 | BE-001, AUTH-ARCH-001 | P0 |
- Legacy line 1317: | AUTH-013 | Create CSRF-protected \`POST /api/auth/register\` endpoint (role=USER always) — ✅ Completed | 2 | AUTH-012, AUTH-011A | P0 |
- Legacy line 1318: | AUTH-014 | Create CSRF-protected \`POST /api/auth/login\` endpoint (sets cookies; returns sanitized user) — ✅ Completed | 2 | AUTH-012, AUTH-011A | P0 |
- Legacy line 1319: | AUTH-015 | Create CSRF-protected \`POST /api/auth/refresh\` endpoint with rotation/reuse detection — ✅ Completed | 2 | AUTH-011, AUTH-011A | P0 |
- Legacy line 1328: | AUTH-024 | Implement session logout endpoint — Backend/live and frontend/cache acceptance PASS | 2 | AUTH-015, AUTH-017, AUTH-011A | P0 |
- Legacy line 1356: | EVS-003 | Create shared Supabase image storage service and bucket policies — ✅ Completed | 3 | BE-004, AUTH-018, AUTH-011A | P0 |
- Legacy line 1361: | BE-012 | Create own-profile read/update endpoints — ✅ Completed | 2 | BE-011, AUTH-017, AUTH-011A | P0 |
- Legacy line 1388: | EVT-006 | Create admin event list, detail, CRUD and status APIs | 3 | EVT-004, AUTH-018, AUTH-011A | P0 |
- Legacy line 1465: | MATCH-010 | Create own-match accept/reject endpoint | 2 | MATCH-009, MATCH-007, AUTH-011A | P0 |
- Legacy line 2123: - Added \`AUTH-011A\` so CSRF service and endpoint work is independently testable before register/login/refresh mutations are implemented.
- Legacy line 2985: **Next Task**: \`AUTH-011A — Create signed CSRF service and GET /api/auth/csrf endpoint\`.
- Legacy line 4266: Done: AUTH-011A               Create signed CSRF service and \`GET /api/auth/csrf\` endpoint [P0; Phase 5; completed 2026-09-16]
- Legacy line 4839: **Dependencies:** AUTH-015, AUTH-017, AUTH-011A
- Legacy line 5241: policies, P0 / Phase 8 / Cx3; dependencies BE-004, AUTH-018 and AUTH-011A DONE, READY. It is not
- Legacy line 5251: **Dependencies:** BE-004, AUTH-018, AUTH-011A
- Legacy line 5411: dependencies BE-011, AUTH-017 and AUTH-011A DONE, READY. It is not implemented here.
- Legacy line 5420: **Dependencies:** BE-011, AUTH-017, AUTH-011A
- Legacy line 6034: **Dependencies:** EVT-004, AUTH-018, AUTH-011A
- Legacy line 6387: **Dependencies:** MATCH-009, MATCH-007, AUTH-011A
- Legacy line 8576: - **Dependencies:** \`EVT-004\`, \`EVT-005\`, \`AUTH-018\`, \`AUTH-011A\`, \`EVT-008\`.
