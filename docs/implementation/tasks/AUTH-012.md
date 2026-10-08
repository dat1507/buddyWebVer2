# AUTH-012

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-008, AUTH-010, AUTH-011

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3080-3173

### AUTH-012 — Create auth service (register, login, verify role)

**Status**: Completed (✅) on 2026-09-17
**Objective**: Provide a transaction-aware service boundary for safe public registration,
credential authentication and exact persisted-role verification without prematurely implementing
the AUTH-013/AUTH-014 HTTP endpoints or refresh-session persistence.

The registry supplied only the task title and dependencies. The operational criteria below make
email identity, account-enumeration, transaction ownership and authorization behavior explicit for
the endpoint tasks that consume this service.

**Operational Acceptance Criteria**:

- [x] Email identities are trimmed, limited to the conservative ASCII mailbox contract, validated
  to 254 total/64 local-part characters, and case-folded before every insert or lookup. Blank,
  malformed, Unicode-ambiguous, whitespace, invalid-label and overlong inputs fail with one
  non-reflective validation error.
- [x] Registration hashes the password without trimming/normalizing it, explicitly stages active,
  unverified role `USER`, and exposes no role argument through which public input could create an
  Admin.
- [x] Registration performs the insert/flush and relies on PostgreSQL's unique constraint as the
  race-safe email authority. SQLSTATE `23505` is rolled back and mapped to generic
  `Account registration failed.` without reflecting the email; unrelated integrity errors remain
  visible to infrastructure handling rather than being mislabeled as duplicates.
- [x] Login looks up only the canonical email, verifies bcrypt for known and unknown accounts,
  rejects missing/wrong-password/inactive/soft-deleted accounts with the same
  `Invalid email or password.` error, and never returns tokens.
- [x] A fixed non-secret cost-12 dummy bcrypt hash prevents the missing-account path from skipping
  the expensive password verification step. Passwords and hashes are not placed in SQL predicates,
  exceptions, logs or result representations.
- [x] Successful login stages a timezone-aware `last_login` and returns the actual database User
  role. It never accepts or trusts the frontend login page, expected role, body role or UI store.
- [x] Role verification requires an active, non-deleted User and the exact persisted `USER` or
  `ADMIN` role; failures use the generic `Insufficient permissions.` message.
- [x] Registration and login flush but do not commit, issue JWTs, set cookies or create refresh
  state. AUTH-013/AUTH-014 and later AUTH-015 retain ownership of the request transaction so account,
  login metadata and session persistence can be committed atomically.
- [x] Focused unit/security tests and a disposable PostgreSQL 17 runtime-role acceptance run prove
  canonical persistence, bcrypt verification, duplicate races, last-login writes and role denial.

**Files Created**:

- `apps/api/app/services/auth.py`
- `apps/api/tests/test_auth_service.py`

**Files Modified**:

- `apps/api/app/services/__init__.py`
- `apps/api/README.md`
- `README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- The service uses the existing bcrypt/User/UserRole contracts without adding a dependency or
  changing lockfiles. The product minimum-strength policy remains owned by the future request
  schema; the existing non-empty/72-byte bcrypt safety boundary is preserved.
- ASCII mailbox validation is deliberately conservative for deterministic identity and uniqueness;
  internationalized mailbox support would require an explicit product decision and dedicated
  normalization dependency rather than silently widening this account-key contract.
- Login performs the database lookup before one bcrypt check for all syntactically valid emails.
  Disabled and soft-deleted accounts still traverse password verification before the same generic
  denial, reducing account-state and identifier enumeration signals.
- Each FastAPI request retains its own `AsyncSession`; service operations are sequential and never
  share a session across concurrent tasks.

**Verification Results**:

- Focused authentication-service suite — PASS, 36 tests.
- Full backend suite — PASS, 162 tests.
- `ruff check .` and Ruff format check for all three changed Python files — PASS.
- `mypy app alembic tests` — PASS, strict mode over 35 source files.
- Python 3.12.10 clean locked dependency install and `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel include the auth service and tests.
- Alembic `history` / `heads` — PASS; `0002_users` remains the only head.
- Docker context `desktop-linux` and Linux Engine 29.8.0 — PASS.
- Disposable PostgreSQL 17 Compose acceptance — PASS: healthy container, migrations at
  `0002_users`, runtime-role register/login/update, persisted `USER`, `last_login`, exact role check
  and duplicate-email generic failure. The isolated container, network and volume were removed.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern repository scan — PASS, no credential-shaped matches.

**Database Changes**: None; the existing `0002_users` schema is sufficient. Live acceptance inserted
only into the disposable database and removed its project-specific volume afterward.
**Environment Variables Added**: None.
**Business API Changes**: None; AUTH-013/AUTH-014 own the public register/login routes.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-012 and does not
block unrelated authentication foundation work.
**Next Task**: `AUTH-013 — Create CSRF-protected POST /api/auth/register endpoint (role=USER always)`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1316: | AUTH-012 | Create auth service (register, login, verify role) — ✅ Completed | 3 | AUTH-008, AUTH-010, AUTH-011 | P0 |
- Legacy line 1317: | AUTH-013 | Create CSRF-protected \`POST /api/auth/register\` endpoint (role=USER always) — ✅ Completed | 2 | AUTH-012, AUTH-011A | P0 |
- Legacy line 1318: | AUTH-014 | Create CSRF-protected \`POST /api/auth/login\` endpoint (sets cookies; returns sanitized user) — ✅ Completed | 2 | AUTH-012, AUTH-011A | P0 |
- Legacy line 2688:   AUTH-012 must trim and canonicalize email before persistence; the model does not mutate input.
- Legacy line 3078: **Next Task**: \`AUTH-012 — Create auth service (register, login, verify role)\`.
- Legacy line 3177: **Objective**: Expose the AUTH-012 registration service through a narrow public HTTP boundary that
- Legacy line 3198: - [x] The endpoint delegates hashing and least-privilege construction to AUTH-012, commits only
- Legacy line 3272: **Objective**: Expose the AUTH-012 credential service through the shared public login endpoint,
- Legacy line 4267: Done: AUTH-012                Create auth service (register, login, verify role) [P0; Phase 5; completed 2026-09-17]
