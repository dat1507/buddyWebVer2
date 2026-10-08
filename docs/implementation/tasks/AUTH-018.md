# AUTH-018

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-017

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3636-3715

### AUTH-018 — Create `require_role(role)` FastAPI dependency (verify role)

**Status**: Completed (✅) on 2026-09-17
**Objective**: Provide one reusable server-declared exact-role dependency that composes verified
authentication with current database authorization for every protected USER or ADMIN route.

**Operational Acceptance Criteria**:

- [x] `require_role(required_role)` accepts a server-owned `UserRole` enum member and fails fast on
  an invalid dependency configuration; no request field, query value or frontend role can choose
  the required role.
- [x] The role dependency composes `require_auth`, so the access-cookie signature and subject plus
  the current active, non-deleted database User are verified before authorization runs.
- [x] Authorization uses exact current persisted role semantics. The signed access-token role is
  never an authority: a current database `ADMIN` passes despite a stale `USER` claim, while a
  database downgrade to `USER` immediately defeats a stale `ADMIN` claim.
- [x] Missing/invalid credentials and missing, inactive or deleted Users retain the shared generic
  no-store `401 Authentication required.` contract. An authenticated wrong-role User receives a
  separate generic no-store `403 Insufficient permissions.` response with neither role disclosed.
- [x] Success returns the same persisted `User` produced by `require_auth` for downstream ownership
  and audit decisions; the dependency does not mutate cookies, tokens, sessions or database state.
- [x] Exact `USER` and `ADMIN` gates, stale-claim cases, client-supplied role attempts, response
  sanitization, inactive/anonymous denial, full regression and disposable PostgreSQL acceptance
  are covered.
- [x] No product endpoint, migration, environment variable or new dependency is introduced ahead
  of its owning task. Later admin and user APIs can now apply this completed boundary.

**Files Created**:

- `apps/api/tests/test_role_dependency.py`

**Files Modified**:

- `apps/api/app/api/dependencies.py`
- `apps/api/README.md`
- `README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- The factory closes over a typed `UserRole` selected in route source code and delegates the actual
  active/deleted/exact-role decision to the completed `verify_user_role` service.
- The dependency translates only `RoleVerificationError` into HTTP 403. Authentication errors from
  `require_auth` remain HTTP 401, preserving an explicit authentication/authorization boundary.
- The generic authorization response is marked `Cache-Control: no-store` and `Pragma: no-cache`;
  it does not reflect expected or actual roles and never sets a cookie.
- The skill-guided change preserves the existing auth service and current-user dependency instead
  of duplicating token or database logic; AUTH-018 is only the smallest authorization adapter.

**Verification Results**:

- AUTH-018 dependency/security suite — PASS, 10 tests; combined role/current-user/auth-service
  focused suite — PASS, 56 tests.
- Full backend suite — PASS, 262 tests.
- `ruff check .` — PASS; Ruff format check for both AUTH-018 Python files — PASS. The optional
  repository-wide format-only check still identifies seven untouched legacy files with pre-existing
  formatting/line-ending differences; no AUTH-018 file is affected.
- `mypy app alembic tests` — PASS, strict mode over 47 source files; `pip check` — PASS.
- `python -m build --no-isolation` — PASS; sdist and wheel contain the role dependency and tests.
- Alembic `history` / `heads` — PASS; existing `0003_refresh_sessions` remains the only head.
- Docker Desktop 4.91.0 / Linux Engine 29.8.0 / Compose 5.5.1 — PASS on `desktop-linux`.
- Disposable PostgreSQL 17 + pgvector 0.8.6 acceptance — PASS: healthy isolated container,
  migrations at `0003`, `alembic check` with no drift, vector distance query, runtime database
  health `200`, DB-authoritative promotion/demotion over stale claims, exact USER gate, generic
  wrong-role `403`, and inactive/anonymous `401`. Its container, network and volume were removed.
- `pip-audit --strict -r requirements.lock` and `npm audit --omit=dev` — PASS, no known
  vulnerabilities.
- Frontend format, lint, type-check, 80 tests and production build — PASS; only the existing
  non-blocking chunk-size warning remains.
- Credential-pattern and AUTH-018 temporary-file/resource scans — PASS.

**Database Changes**: None; AUTH-018 reads the existing `app_private.users` authorization state
through AUTH-017. Live acceptance used and removed an isolated Compose volume.
**Environment Variables Added**: None.
**Business API Changes**: None; this task adds the reusable dependency for later protected routes.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-018 and does not
block unrelated authentication core work.
**Next Task**: `AUTH-019 — Create admin seed CLI command (python -m app.cli create-admin)`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1322: | AUTH-018 | Create \`require_role(role)\` FastAPI dependency (verify role) — ✅ Completed | 2 | AUTH-017 | P0 |
- Legacy line 1356: | EVS-003 | Create shared Supabase image storage service and bucket policies — ✅ Completed | 3 | BE-004, AUTH-018, AUTH-011A | P0 |
- Legacy line 1362: | BE-013 | Create authorized admin user list and detail reads — ✅ Completed | 2 | BE-011, AUTH-018, EVT-008 | P0 |
- Legacy line 1388: | EVT-006 | Create admin event list, detail, CRUD and status APIs | 3 | EVT-004, AUTH-018, AUTH-011A | P0 |
- Legacy line 1405: | EVS-006 | Create Admin EventSlider CRUD, status, visibility, reorder, and upload endpoints | 4 | EVS-004, AUTH-018 | P0 |
- Legacy line 1463: | MATCH-008 | Create admin matching run and preview persistence | 3 | MATCH-004, AUTH-018, EVT-008 | P0 |
- Legacy line 3321:   APIs independently reload authorization state through AUTH-017/AUTH-018.
- Legacy line 3477: database-role authority and the boundary with AUTH-016/AUTH-018 explicit.
- Legacy line 3518:   read and AUTH-018 owns exact role enforcement.
- Legacy line 3634: **Next Task**: \`AUTH-018 — Create require_role(role) FastAPI dependency (verify role)\`.
- Legacy line 4273: Done: AUTH-018                Create \`require_role(role)\` FastAPI dependency (verify role) [P0; Phase 5; completed 2026-09-17]
- Legacy line 5241: policies, P0 / Phase 8 / Cx3; dependencies BE-004, AUTH-018 and AUTH-011A DONE, READY. It is not
- Legacy line 5251: **Dependencies:** BE-004, AUTH-018, AUTH-011A
- Legacy line 5447: Cx2; dependencies BE-011, AUTH-018 and EVT-008 DONE, READY. It is not implemented here.
- Legacy line 5456: **Dependencies:** BE-011, AUTH-018, EVT-008
- Legacy line 6034: **Dependencies:** EVT-004, AUTH-018, AUTH-011A
- Legacy line 6326: **Dependencies:** MATCH-004, AUTH-018, EVT-008
- Legacy line 6889: | SEM-005 (**Done 2026-10-02**) | Safe reset execution | SEM-004, AUTH-018, EVT-008 | Re-auth, write barrier, verified backup, USER data deletion only | Destructive staging tests |
- Legacy line 7805: - **Dependencies / ownership:** INV-006, BUDDY-002, existing AUTH-018/EVT-008; Backend.
- Legacy line 7998: - **Dependencies / ownership:** SEM-004, AUTH-018, EVT-008; Backend + Database + Storage + Operations.
- Legacy line 8190: (SEM-004 + AUTH-018 + EVT-008) → SEM-005 → SEM-006
- Legacy line 8576: - **Dependencies:** \`EVT-004\`, \`EVT-005\`, \`AUTH-018\`, \`AUTH-011A\`, \`EVT-008\`.
