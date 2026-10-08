# AUTH-010

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** BE-001

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2813-2892

### AUTH-010 — Create password hashing service (bcrypt)

**Status**: Completed (✅) on 2026-09-16
**Objective**: Provide the shared application-owned password hashing and verification primitives
needed by registration, login, admin seeding and future password changes.

The registry specified bcrypt with 12 rounds but did not define a dedicated password-service
contract. The operational acceptance criteria below establish the technical security boundary;
product password-strength and minimum-length policy remains owned by the future input schemas.

**Operational Acceptance Criteria**:

- [x] The service hashes UTF-8 passwords directly with bcrypt `2b`, cost 12 and a fresh
  cryptographically secure salt for every hash.
- [x] Only the encoded bcrypt hash is returned. The service does not trim, Unicode-normalize, log,
  persist or otherwise expose plaintext passwords.
- [x] Empty passwords and values longer than bcrypt's 72-byte limit are rejected during hash
  creation; length is measured after UTF-8 encoding and no silent truncation occurs.
- [x] Verification delegates comparison to `bcrypt.checkpw` and returns `False` for wrong,
  empty or overlong candidates and malformed/non-ASCII stored hashes instead of surfacing an
  authentication error.
- [x] Boundary coverage includes random salts, correct and wrong candidates, exact whitespace,
  Unicode normalization differences, exactly 72 bytes, multibyte input, overlong input and corrupt
  stored hashes.
- [x] Bcrypt is a pinned runtime dependency in both reproducible Python 3.12 lockfiles; clean
  install, package build, dependency consistency and vulnerability audit pass.
- [x] No account, database, API route, password-strength rule, JWT/cookie or persistent session
  behavior is introduced.

**Files Created**:

- `apps/api/app/services/passwords.py`
- `apps/api/tests/test_passwords.py`

**Files Modified**:

- `apps/api/app/services/__init__.py`
- `apps/api/pyproject.toml`
- `apps/api/requirements.lock`
- `apps/api/requirements-dev.lock`
- `apps/api/README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- Used `bcrypt` directly rather than an additional password-framework abstraction. The locked
  runtime version is `bcrypt==5.0.0` and the service explicitly requests prefix `2b` and cost 12.
- Centralized the algorithm constraints as `BCRYPT_ROUNDS` and `BCRYPT_MAX_PASSWORD_BYTES` so
  later registration/password-change schemas can enforce the same byte boundary.
- Hash creation raises a domain-specific `PasswordHashingError` for invalid technical input;
  verification intentionally fails closed to avoid converting malformed attacker-controlled data
  into a server error.
- Did not pre-hash, trim or normalize input because doing so would alter the user's secret and
  expand the contract beyond the implementation plan. A future algorithm migration can be handled
  explicitly with versioned hashes if required.

**Verification Results**:

- Focused password-service suite — PASS, 11 tests.
- Full backend suite — PASS, 69 tests.
- `ruff check .` — PASS.
- `mypy app alembic tests` — PASS, strict mode over 27 source files.
- Python 3.12 clean locked dependency install and `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel include the password service.
- Alembic `history` / `heads` — PASS; `0002_users` remains the only head.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern repository scan — PASS, no credential-shaped matches.

**Database Changes**: None; AUTH-010 is a pure application service and did not require Docker or a
live database acceptance run.
**Environment Variables Added**: None.
**Business API Changes**: None.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-010 and does not
block unrelated authentication foundation work.
**Next Task**: `AUTH-011 — Create JWT cookie service (create/verify access + rotating refresh tokens)`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1313: | AUTH-010 | Create password hashing service (bcrypt) — ✅ Completed | 2 | BE-001 | P0 |
- Legacy line 1316: | AUTH-012 | Create auth service (register, login, verify role) — ✅ Completed | 3 | AUTH-008, AUTH-010, AUTH-011 | P0 |
- Legacy line 1323: | AUTH-019 | Create admin seed CLI command (\`python -m app.cli create-admin\`) — ✅ Completed | 2 | AUTH-008, AUTH-010 | P0 |
- Legacy line 1329: | AUTH-025 | Implement authenticated password change endpoint | 2 | AUTH-024, AUTH-010 | P1 |
- Legacy line 2811: **Next Task**: \`AUTH-010 — Create password hashing service (bcrypt)\`.
- Legacy line 4264: Done: AUTH-010                Create password hashing service (bcrypt) [P0; Phase 5; completed 2026-09-16]
- Legacy line 6522: **Dependencies:** AUTH-024, AUTH-010
