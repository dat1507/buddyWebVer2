# AUTH-024

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-015, AUTH-017, AUTH-011A

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3823-3869

### AUTH-024 — Session logout endpoint

**Status**: Implemented; backend/local/live acceptance PASS (2026-09-17). Overall cross-task
acceptance remains **PARTIAL**: frontend session/private-cache clearing is owned by
AUTH-004/AUTH-021 and is not implemented or claimed verified here. Backend dependency is satisfied,
so this outstanding frontend acceptance does not block development of AUTH-004.

- Added cookie-only `POST /api/auth/logout`, empty `204`; exact trusted origin and signed
  session-bound CSRF are mandatory when either cookie identifies a valid family. Valid refresh is
  preferred, so expired access does not trap users. Verified access is a fallback when refresh is
  missing/invalid; no User/verification/role gate prevents wrong-role or inactive-account cleanup.
- Owner-bound `sid`/`sub` selection and the refresh service's `FOR UPDATE` lock serialize logout
  against rotation. Stale JTI logout revokes the latest family member. Other families are unaffected.
  Missing/deleted/revoked rows are indistinguishable idempotent no-ops. Commit precedes clearing all
  three host-only cookies; SQLAlchemy failures roll back with generic no-store `503` and no cookies.
- Anonymous/invalid-credential cleanup requires a fresh signed pre-auth CSRF context and trusted
  origin; it has no database query/commit and does not claim server revocation. An unprotected repeat
  still gets `403`. The configured database session factory remains required (no connection used).
- Added logout to the existing 120/minute transport-IP gate. No role quota is applied to logout;
  USER 120/minute and ADMIN 60/minute quotas elsewhere remain unchanged. IP quota/storage errors
  still fail closed (`429`/Retry-After or `503`); production operator gate is unchanged.
- 35 logout unit/security checks + 5 opt-in PostgreSQL/Redis live cases PASS. Full backend **365
  tests PASS on Python 3.14 and 3.12**, including AUTH-020 shared Redis regression. Real row-lock
  wait observed in both race orders; login/logout/replay/isolation/runtime DB health PASS.
- Ruff lint/changed-file format, strict mypy (55 files), pip check, sdist/wheel build and pip-audit
  PASS; frontend format/lint/typecheck/**80 tests**/build/npm audit PASS. Existing 513.01 kB frontend
  chunk warning only. Alembic upgrade to `0003_refresh_sessions` and schema-drift check PASS against
  a disposable database; no schema/compose/dependency/runtime config change, so no new downgrade
  migration is required. Docker Desktop 4.91.0/Engine 29.8.0, `desktop-linux`, verified running.
- Acceptance isolation: project `vgu_auth024_acceptance` (PostgreSQL port 55441/database
  `vgu_buddy_auth024`) and task-labelled Redis on 56381. Ownership labels were checked before
  removing only these test containers/network/database volume. Post-cleanup inventory empty;
  disposable test data removed, reproducible by migrations/tests. Existing images/dev data untouched.
- Files: modified root README, API README, `app/api/auth.py`, `app/core/rate_limits.py`,
  `app/services/refresh_sessions.py` and this plan; created `tests/test_auth_logout.py` and
  `tests/test_auth_logout_live.py`. No secret/actual .env change; only public synthetic fixtures.
- **Access-token limitation:** existing AUTH-017 does not consult refresh-family revocation. A
  copied access JWT may work until its 15-minute TTL + 30-second skew. In-flight refresh may also
  deliver cookies after logout; its family still cannot refresh. No immediate access denylist is
  claimed. AUTH-021 must coordinate these frontend requests and invalidate private query caches.
- Production Redis/TLS/trusted-ingress/deployed smoke remains **not verified** (AUTH-020). Gemini
  remains **⚠️ Still pending — revoke before any future Gemini/chatbot integration.**

**Next development task**: `AUTH-004 — Create non-persisted Zustand session store`; not executed here.

---


### Legacy lines 4834-4856

### AUTH-024 — Implement session logout endpoint

**Task ID:** `AUTH-024`
**Change:** New; **Status:** Implemented; backend/live and combined frontend/cache acceptance PASS (integration 2026-09-18); **Priority:** P0; **Phase:** 5
**Goal:** Make the approved logout and wrong-role admin-login flows executable.
**Dependencies:** AUTH-015, AUTH-017, AUTH-011A
**Scope:** POST /api/auth/logout; revoke refresh session and clear cookies.

**Acceptance Criteria:**

- [x] CSRF-protected logout revokes the current refresh session and clears auth/CSRF cookies; repeated logout safely clears cookies. — Unit/security and real PostgreSQL/Redis API acceptance PASS.
- [x] A revoked refresh token cannot mint another session; frontend clears session and private query caches. — Existing backend replay/race acceptance retained; AUTH-021 PostgreSQL live replay/revocation PASS, real browser logout persists family revocation, frontend clears AUTH-004 and cancels/removes private queries while public slider cache survives. Late rotation/private-response and account-switch tests PASS.

**Out of Scope:** New authentication transport, logout UI redesign.

**Verified contract/evidence (2026-09-17):** Empty no-store `204`; trusted-origin signed session
CSRF with verified cookie identity, or fresh pre-auth CSRF for anonymous cookie cleanup only. Commit
owner-bound family revocation before expiring all three cookies. See PART 18B AUTH-024 execution
record and `apps/api/README.md` for repeat/error flows, IP-only quota, test commands and access-token
residual TTL. 35 unit/security + 5 live tests PASS; full backend 365 PASS (Python 3.14/3.12), frontend
80 regression tests/quality gates PASS. No browser session-client/cache/logout UI acceptance claim.
Production release still requires AUTH-020 operator configuration/smoke; Gemini remediation pending.


## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1325: | AUTH-021 | Connect session client, registration, and auth bootstrap — ✅ Completed | 2 | AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024 | P0 |
- Legacy line 1328: | AUTH-024 | Implement session logout endpoint — Backend/live and frontend/cache acceptance PASS | 2 | AUTH-015, AUTH-017, AUTH-011A | P0 |
- Legacy line 1329: | AUTH-025 | Implement authenticated password change endpoint | 2 | AUTH-024, AUTH-010 | P1 |
- Legacy line 2168: cache invalidation. AUTH-024's combined frontend AC remains unchecked. Existing access JWT residual
- Legacy line 3049:   AUTH-014/AUTH-015/AUTH-024.
- Legacy line 3327:   AUTH-024 later revokes that state and clears all cookies.
- Legacy line 3430: - Failed refresh does not claim logout or clear cookies. AUTH-024 owns explicit family revocation
- Legacy line 3821: **Next development task**: \`AUTH-024 — Implement session logout endpoint\`; not executed by AUTH-020.
- Legacy line 4276: Done: AUTH-024                Backend/live and frontend/cache integration acceptance PASS [P0; Phase 5; integration completed 2026-09-18]
- Legacy line 4375: Shared: **BE-001 → BE-002..007 → Auth Backend/RBAC + AUTH-024 → AUTH-004..006/021..023 → guarded layouts**, plus EVT-008 audit and EVS-003 storage.
- Legacy line 4582: source. No live browser/deployed auth claim. AUTH-024 frontend/cache AC remains pending AUTH-021.
- Legacy line 4862: **Dependencies:** AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024
- Legacy line 6522: **Dependencies:** AUTH-024, AUTH-010
