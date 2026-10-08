# AUTH-019

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-008, AUTH-010

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3716-3800

### AUTH-019 — Create admin seed CLI command (`python -m app.cli create-admin`)

**Status**: Completed (✅) on 2026-09-17
**Objective**: Provide a trusted, explicit deployment command that creates an initial Admin without
exposing any public role-assignment API or silently modifying an existing account.

**Operational Acceptance Criteria**:

- [x] `python -m app.cli create-admin --email <email>` uses a hidden password prompt plus
  confirmation. `--password-stdin` supports non-interactive secret delivery. Command-line
  `--password` and `--password=<value>` forms are rejected so secrets cannot enter shell history
  or process listings.
- [x] The command uses only server-side `DATABASE_URL`, canonicalizes the email, requires at least
  15 characters and at most 72 UTF-8 bytes, then hashes the exact password with bcrypt cost 12.
- [x] A successful transaction creates one `ADMIN` with `is_active=true`,
  `email_verified=true`, no deletion timestamp and no login/session/token side effect.
- [x] The service flushes but does not commit; the CLI owns the transaction, commits once on
  success, rolls back commit failures and disposes the process engine in all outcomes.
- [x] Duplicate addresses fail closed with a sanitized non-zero exit. Existing USER or ADMIN rows
  are not promoted, reactivated, password-reset, or otherwise changed.
- [x] Invalid email, weak/overlong password, database configuration and database availability
  failures never reflect a password, URL, credential or internal diagnostic in terminal output.
- [x] No API endpoint, startup hook, `INITIAL_ADMIN_*` environment contract, migration or external
  dependency is introduced. Future automatic bootstrap/invitation behavior remains separate work.
- [x] Unit/CLI transaction tests, full regression and disposable PostgreSQL acceptance prove
  persistence, hashing, authentication, duplicate/no-promotion behavior and sanitized errors.

**Files Created**:

- `apps/api/app/cli.py`
- `apps/api/tests/test_admin_cli.py`

**Files Modified**:

- `apps/api/app/services/auth.py`
- `apps/api/app/services/__init__.py`
- `apps/api/tests/test_structure.py`
- `apps/api/README.md`
- `README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- Standard-library `argparse` and `getpass` satisfy the small CLI contract without adding Click or
  another production dependency. Hidden prompting is the operator default; stdin is the preferred
  automation channel.
- `create_admin` reuses canonical email and password primitives but exposes no role argument. Its
  role, active state and verified state are fixed server-side.
- Unique enforcement remains race-safe in PostgreSQL. The CLI never upgrades an account just
  because its email matches the requested Admin address.
- The skill-guided change preserves the existing auth and database transaction boundaries while
  adding the smallest testable operational adapter; no API startup behavior was broadened.

**Verification Results**:

- AUTH-019 Admin service/CLI suite — PASS, 17 tests; combined Admin/auth/password focused suite —
  PASS, 64 tests.
- Full backend suite — PASS, 280 tests.
- `ruff check .` and Ruff format checks for all five modified AUTH-019 Python files — PASS.
- `mypy app alembic tests` — PASS, strict mode over 49 source files; `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel contain `app/cli.py` and its tests.
- CLI top-level/create-admin help smoke tests — PASS; argument surface is email plus mutually
  exclusive password, password-stdin or hidden-prompt input.
- Alembic `history` / `heads` — PASS; existing `0003_refresh_sessions` remains the only head.
- Docker Linux Engine 29.8.0 / Compose 5.5.1 — PASS on `desktop-linux`.
- Disposable PostgreSQL 17 + pgvector 0.8.6 acceptance — PASS: healthy isolated container,
  migrations at `0003`, `alembic check` with no drift, vector distance query, real runtime-role CLI
  commit, canonical active/verified ADMIN, bcrypt verification and login, duplicate/weak-password
  non-zero exits, existing USER preserved, and API database health `200`. Its container, network
  and volume were removed afterward.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern and AUTH-019 temporary-file/resource scans — PASS.

**Database Changes**: None; the CLI writes the existing `app_private.users` model. Live acceptance
created rows only inside a removed disposable Compose volume.
**Environment Variables Added**: None; the existing server-only `DATABASE_URL` is reused.
**Business API Changes**: None; Admin privilege creation remains outside HTTP routes.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-019 and does not
block unrelated authentication core work.
**Next Task**: `AUTH-020 — Create rate limiting middleware (slowapi)`.


### Legacy lines 4181-4200

### Operator CLI Seed — Implemented by AUTH-019

Run `python -m app.cli create-admin --email admin@vgu.edu.vn` for a hidden password prompt and
confirmation. Non-interactive deployment can pass one password line with `--password-stdin`.
Command-line `--password` and `--password=<value>` forms are rejected because process listings and
shell history may expose command-line arguments.

The command uses the configured least-privilege `DATABASE_URL`, canonicalizes the email, applies
the shared bcrypt boundary, and commits one active, verified `ADMIN`. Duplicate email and weak or
invalid credentials exit non-zero. Existing USER/ADMIN rows are never promoted, reactivated,
reset, or otherwise modified, and database failures roll back with sanitized terminal output.

No startup hook or `INITIAL_ADMIN_*` environment contract is implemented. An automatic bootstrap
would need a separate task to define concurrency, rotation, secret delivery and idempotency.

> [!NOTE]
> **Future expansion**: Add admin invitation flow where existing ADMIN can invite new admins via email. Not needed at MVP.

---


## Cross-reference occurrences outside extracted headings

- Legacy line 1007: AUTH-019 implements only this explicit operator command. The API does not auto-create an Admin at
- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1323: | AUTH-019 | Create admin seed CLI command (\`python -m app.cli create-admin\`) — ✅ Completed | 2 | AUTH-008, AUTH-010 | P0 |
- Legacy line 3714: **Next Task**: \`AUTH-019 — Create admin seed CLI command (python -m app.cli create-admin)\`.
- Legacy line 4274: Done: AUTH-019                Create admin seed CLI command (\`python -m app.cli create-admin\`) [P0; Phase 5; completed 2026-09-17]
- Legacy line 4397: The final acceptance is a gate, not a new implementation task: create one Admin through AUTH-019, register one Vietnamese and one international USER through AUTH-013/AUTH-021, complete both profiles through the existing Profile flow, run/preview/publish through the new Admin UI, accept from both user sessions, and verify the active Buddy result after reload. It must use PostgreSQL and the configured private storage service; no fake users, fake match result or frontend-only success state may satisfy it.
