# AUTH-004

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** FE-001, AUTH-ARCH-001 (both completed).

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2136-2180

### AUTH-004 — Non-persisted Zustand session store

**Status**: COMPLETED (2026-09-17). Contract derived from Phase 4 registry and approved
AUTH-ARCH-001; detailed operational acceptance is recorded in PART 25. No auth UI wiring performed.

**Implemented**:

- `src/stores/auth-store.ts`: typed status/user/role union, initial neutral `unknown`, atomic
  `startLoading`, `setAuthenticated`, repeat-safe `clearSession` and neutral `resetSession` actions.
  Non-authenticated states always clear user/role; role comes only from the validated User DTO.
- `src/features/auth/session-user.ts`: strict UUID, non-empty email string, USER/ADMIN role and
  boolean `email_verified`; projects only four scalar fields, copies/freezes User and exposes no
  raw payload/Zod diagnostics on failure. Invalid input clears the previous identity (fail closed).
- Zustand **5.0.15** added explicitly, compatible with current React 19.2.8. No persistence/devtools
  middleware, JWT/CSRF fields, storage/cookie/network side effects, backend/schema/env changes.
- Colocated validation/store tests use actual Zustand, React hook selectors, all-state transitions,
  account switching, payload extras, reference mutation, invalid-input sanitization, storage/cookie/
  IndexedDB/network spies and fresh-module reload with stale Web Storage.

**Verification (2026-09-17)**: 41 AUTH-004 tests; full frontend **121/121 PASS**. Prettier, ESLint,
strict TypeScript, production build and npm audit (runtime + dev) PASS; existing 513.01 kB chunk
warning remains. `npm ci` PASS with unchanged lockfile hash. It also reports baseline ESLint 9.39.5
deprecation: ESLint v9 reached EOL on 2026-08-06 ([official support status](https://eslint.org/version-support/)).
Track a separate compatible tooling upgrade; no major lint-stack change in AUTH-004, no detected
npm vulnerabilities. Backend regression **355 PASS, 10 opt-in live checks explicitly skipped** (no DB/Redis
started for frontend-only work); backend Ruff/strict mypy PASS. No live browser/bootstrap/logout
acceptance or deployed production verification claimed.

**Boundaries**: This is client presentation, not authorization; backend role/cookie checks remain
authoritative. Use actions, not native `setState`, for payload mutation. `clearSession` clears only
the store, not server cookies/session or private query caches. AUTH-021 still owns `/api/auth/me`,
credentialed transport, single-flight refresh, late-response coordination and integrated logout/
cache invalidation. AUTH-024's combined frontend AC remains unchecked. Existing access JWT residual
TTL and AUTH-020 production operator gate are unchanged. Gemini remains
**⚠️ Still pending — revoke before any future Gemini/chatbot integration.**

**Files**: Created the schema/store and two colocated test files; modified web package/lockfile,
frontend/API/root READMEs and this plan. Zustand is the only added dependency; no .env/production
secret change.

**Next development task**: `AUTH-021 — Connect session client, registration, and auth bootstrap`;
not implemented by AUTH-004.

---


### Legacy lines 4562-4583

### AUTH-004 — Create non-persisted Zustand session store

**Task ID:** `AUTH-004`
**Status:** COMPLETED (✅) on 2026-09-17; **Priority:** P0; **Phase:** 4
**Dependencies:** FE-001, AUTH-ARCH-001 (both completed).
**Goal:** Provide an in-memory presentation of the backend-owned session without token storage.
**Scope:** Zustand store and shared sanitized User types/validation, ready for AUTH-021 integration.

**Operational Acceptance Criteria** (derived from the registry and AUTH-ARCH-001 before coding):

- [x] Fresh store starts `unknown` with null user/role; explicit loading/authenticated/unauthenticated/reset transitions work. — All-state transition and fresh-module tests PASS.
- [x] Authenticated state retains only sanitized User fields and role; role updates atomically with User and cannot retain a previous account through supported actions. — USER/ADMIN, switching and subscription tests PASS; malformed data clears previous identity.
- [x] No JWT, refresh token, password/hash, CSRF or private-profile fields retained; no persistence/storage, cookie or network access. — Payload projection/immutability and storage/cookie/IndexedDB/network checks PASS.
- [x] React selectors update; clear/reset preserve reusable actions; reload ignores stale Web Storage and requires later `/api/auth/me` bootstrap. — Actual Zustand + React hook and isolated fresh-module tests PASS.
- [x] Existing UI-only auth/public routes and quality gates remain healthy. — Full frontend 121 tests, format/lint/strict typecheck/build/npm audit PASS; backend regression 355 PASS/10 explicit opt-in skips.

**Out of Scope:** API/client bootstrap, refresh/retry, actual logout/cache invalidation, login wiring,
route guards, production deployment, Gemini. These remain AUTH-021/022/023/005/006 or existing gates.
**Evidence:** See PART 18A AUTH-004 record and `apps/web/README.md`; 41 dedicated tests, Zustand
5.0.15 pinned with lockfile. Store is a client-only SPA singleton, never a backend authorization
source. No live browser/deployed auth claim. AUTH-024 frontend/cache AC remains pending AUTH-021.


## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1282: | AUTH-004 | Create non-persisted Zustand session store (status, user, role; no tokens) — ✅ COMPLETED | 2 | FE-001, AUTH-ARCH-001 | P0 |
- Legacy line 1283: | AUTH-005 | Create ProtectedRoute component (requires auth) — ✅ Completed | 2 | AUTH-004, FE-006 | P0 |
- Legacy line 1325: | AUTH-021 | Connect session client, registration, and auth bootstrap — ✅ Completed | 2 | AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024 | P0 |
- Legacy line 3827: AUTH-004/AUTH-021 and is not implemented or claimed verified here. Backend dependency is satisfied,
- Legacy line 3828: so this outstanding frontend acceptance does not block development of AUTH-004.
- Legacy line 3866: **Next development task**: \`AUTH-004 — Create non-persisted Zustand session store\`; not executed here.
- Legacy line 4277: Done: AUTH-004                Create non-persisted Zustand session store (status, user, role; no tokens) [P0; Phase 4; completed 2026-09-17]
- Legacy line 4375: Shared: **BE-001 → BE-002..007 → Auth Backend/RBAC + AUTH-024 → AUTH-004..006/021..023 → guarded layouts**, plus EVT-008 audit and EVS-003 storage.
- Legacy line 4588: **Dependencies:** AUTH-004, FE-006; current AUTH-021 bootstrap integration is reused.
- Legacy line 4626: **Dependencies:** AUTH-005; reuses AUTH-004 sanitized role and AUTH-021 verified bootstrap.
- Legacy line 4845: - [x] A revoked refresh token cannot mint another session; frontend clears session and private query caches. — Existing backend replay/race acceptance retained; AUTH-021 PostgreSQL live replay/revocation PASS, real browser logout persists family revocation, frontend clears AUTH-004 and cancels/removes private queries while public slider cache survives. Late rotation/private-response and account-switch tests PASS.
- Legacy line 4862: **Dependencies:** AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024
