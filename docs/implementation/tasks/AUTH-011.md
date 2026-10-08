# AUTH-011

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** BE-001, AUTH-ARCH-001

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2893-2986

### AUTH-011 — Create JWT cookie service (create/verify access + rotating refresh tokens)

**Status**: Completed (✅) on 2026-09-16
**Objective**: Provide hardened JWT creation/verification, cookie transport, and the cryptographic
half of one-use refresh rotation without implementing auth endpoints or pretending stateless JWTs
can detect replay.

The registry and AUTH-ARCH-001 fixed the browser transport and lifetimes but did not specify a JWT
algorithm, claim schema, signing-key contract, token-confusion controls, cookie names or the
stateful boundary required for refresh reuse detection. The operational acceptance criteria below
make those security decisions explicit for dependent auth tasks.

**Operational Acceptance Criteria**:

- [x] Access and refresh JWTs use pinned HS256 with a dedicated URL-safe-base64 signing secret that
  decodes to at least 32 bytes; configuration is server-only, lazy-loaded, redacted and secure by
  default.
- [x] Access tokens expire after 15 minutes and refresh tokens after seven days. Both require
  `iss`, `aud`, `sub`, `sid`, `jti`, `token_type`, `iat`, `nbf` and `exp`; access additionally
  requires a valid `USER`/`ADMIN` role.
- [x] Verification hardcodes the algorithm and validates JOSE `typ`, issuer, strict single
  audience, signature, temporal claims, exact lifetime, UUID identifiers, role and expected token
  type. Malformed, expired, future, wrong-key and untrusted-claim inputs return one sanitized error.
- [x] Every pair has fresh access/refresh `jti` values; a new login may generate a fresh `sid` and a
  prepared rotation preserves that `sid` while returning the consumed refresh `jti` and two new
  token identifiers.
- [x] Token strings are excluded from dataclass representations and are never returned through a
  business API in this task.
- [x] Production cookies are host-only `__Host-` cookies with `Secure`, `HttpOnly`, `SameSite=Lax`,
  `Path=/`, no `Domain`, fixed Max-Age/Expires and no-store response headers. Explicit local HTTP
  mode uses distinct non-`__Host-` `_dev` names and omits only `Secure`.
- [x] Cookie clearing uses matching names/scope/security attributes so production and local
  sessions are expired reliably.
- [x] Rotation does not claim stateless replay protection. AUTH-015 must atomically compare/consume
  the persisted refresh `jti` before sending replacements and revoke the session family on reuse.
- [x] No auth/CSRF endpoint, refresh-session table, persistent revocation state, frontend token
  storage, account mutation or database change is introduced.

**Files Created**:

- `apps/api/app/services/tokens.py`
- `apps/api/tests/test_auth_tokens.py`

**Files Modified**:

- `apps/api/app/core/config.py`
- `apps/api/app/services/__init__.py`
- `apps/api/.env.example`
- `apps/api/pyproject.toml`
- `apps/api/requirements.lock`
- `apps/api/requirements-dev.lock`
- `apps/api/README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- Selected HS256 because the monolithic FastAPI backend is both the only issuer and the only
  verifier. A fixed algorithm allowlist plus a dedicated 256-bit-or-larger random secret avoids
  algorithm/key confusion without adding unnecessary public-key infrastructure.
- Locked `PyJWT==2.14.0`. Decode never derives the algorithm or verification key from attacker-
  controlled header fields and does not accept `none` or alternate token types.
- The refresh token intentionally omits role. Rotation accepts the current database role so role
  changes are reflected when AUTH-015 issues a new access token; AUTH-017 must still reload active,
  non-deleted user state and authoritative role on protected requests.
- A 30-second clock-skew allowance covers normal host drift, while exact signed lifetimes prevent a
  mistakenly extended token from being accepted.
- Added `AUTH_JWT_SECRET` and `AUTH_COOKIE_SECURE`. The latter defaults to production-safe `true`;
  `false` is an explicit local HTTP development exception only.

**Verification Results**:

- Focused JWT/config/cookie suite — PASS, 28 tests.
- Full backend suite — PASS, 97 tests.
- `ruff check .` — PASS.
- `mypy app alembic tests` — PASS, strict mode over 29 source files.
- Python 3.12 clean locked dependency install and `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel include the token service.
- Alembic `history` / `heads` — PASS; `0002_users` remains the only head.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern repository scan — PASS, no credential-shaped matches.

**Database Changes**: None; AUTH-011 is a pure token/cookie service and did not require Docker or a
live database acceptance run. Persistent refresh-session state remains explicitly owned by
AUTH-015.
**Environment Variables Added**: `AUTH_JWT_SECRET`, `AUTH_COOKIE_SECURE`.
**Business API Changes**: None.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-011 and does not
block unrelated authentication foundation work.
**Next Task**: `AUTH-011A — Create signed CSRF service and GET /api/auth/csrf endpoint`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1314: | AUTH-011 | Create JWT cookie service (create/verify access + rotating refresh tokens) — ✅ Completed | 3 | BE-001, AUTH-ARCH-001 | P0 |
- Legacy line 1316: | AUTH-012 | Create auth service (register, login, verify role) — ✅ Completed | 3 | AUTH-008, AUTH-010, AUTH-011 | P0 |
- Legacy line 1319: | AUTH-015 | Create CSRF-protected \`POST /api/auth/refresh\` endpoint with rotation/reuse detection — ✅ Completed | 2 | AUTH-011, AUTH-011A | P0 |
- Legacy line 1321: | AUTH-017 | Create verified-current-user authentication dependency — ✅ Completed | 2 | AUTH-011, AUTH-009 | P0 |
- Legacy line 2891: **Next Task**: \`AUTH-011 — Create JWT cookie service (create/verify access + rotating refresh tokens)\`.
- Legacy line 4265: Done: AUTH-011                Create JWT cookie service (create/verify access + rotating refresh tokens) [P0; Phase 5; completed 2026-09-16]
- Legacy line 4537: **Dependencies:** AUTH-011, AUTH-009
