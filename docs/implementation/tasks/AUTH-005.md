# AUTH-005

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-004, FE-006; current AUTH-021 bootstrap integration is reused.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 4584-4621

### AUTH-005 — Create ProtectedRoute component (requires auth)

**Task ID:** `AUTH-005`
**Status:** COMPLETED (✅) on 2026-09-18; **Priority:** P0; **Phase:** 4
**Dependencies:** AUTH-004, FE-006; current AUTH-021 bootstrap integration is reused.
**Goal:** Gate private route rendering on verified session state without reload redirect flicker.
**Scope:** Reusable outlet guard, User/Admin route integration and neutral localized pending UI.

The Phase 4 registry provides title/dependencies only. These operational acceptance checks derive
from that registry and the approved AUTH-ARCH-001 guard contract, rather than a new role policy:

- [x] `unknown`/`loading` show accessible neutral EN/DE pending; private children/layouts do not mount and the requested URL remains intact. — All-state tests, child mount/unmount checks and unknown base-route tests PASS.
- [x] Confirmed `unauthenticated` redirects with history replacement to the fixed internal login surface; public routes stay reachable. — User/Admin direct/deep-link, Back-history, path/search/hash state and public route integration tests PASS.
- [x] Validated `authenticated` renders the nested outlet and existing index routes; store clear/re-verification removes private content immediately. — Actual Zustand/router selector transitions, USER/ADMIN outlet and logout/account-loading checks PASS.
- [x] AUTH-021 reload/refresh remains bounded without early private UI; existing auth/public/cache regressions and required gates pass. — StrictMode bootstrap, held final `/me` 200/401, rejected refresh, 503 feedback and pending logout/private-public cache tests PASS; real local browser cookies/database reload/logout acceptance PASS.

**Implementation:** Added `features/auth/protected-route.tsx` and two colocated test files; wrapped
all declared `/user` and `/admin` descendants in App. Anonymous login paths are `/login` and
`/adminLogin`; router state preserves only pathname/search/hash and is not consumed as a redirect.
No network/storage/cookie side effects in the guard. EN/DE copy added. A focused test exposed
AUTH-021 installing refreshed identity before bootstrap's final `/me`; bootstrap now validates
refresh User but keeps loading until `/me` succeeds. Ordinary private-request refresh is unchanged.

**Verification:** **31 focused tests PASS; full frontend 206 PASS**, Prettier/ESLint/strict
TypeScript/production build PASS. Full backend **384 PASS / 10 existing Redis live SKIP** with
3 isolated PostgreSQL live cases enabled; backend Ruff/strict mypy (57 files)/pip check PASS.
Production npm audit and strict pip-audit PASS; Git diff/credential signature review PASS with
no .env/config/dependency change or generated/lab file in Git scope.
Real browser verifies anonymous User/Admin redirects, authenticated profile deep-link reload
retaining query/hash, immediate logout redirect and denied re-entry, EN/DE surfaces, empty error
console. No source backend, dependencies, runtime .env, migrations or secrets changed.

**Out of Scope:** AUTH-006 role isolation, AUTH-022/023 login role checks/redirects, layout/profile
features, immediate access denylisting, cross-tab locking and production deployment. Authentication
guard alone permits either valid role; backend authorization remains authoritative. Existing
frontend chunk advisory, AUTH-020 production operator gate and Gemini remediation remain pending.
**Next development task:** AUTH-006 — RoleGuard; not started by AUTH-005.


## Cross-reference occurrences outside extracted headings

- Legacy line 1283: | AUTH-005 | Create ProtectedRoute component (requires auth) — ✅ Completed | 2 | AUTH-004, FE-006 | P0 |
- Legacy line 1284: | AUTH-006 | Create RoleGuard component (requires specific role) — ✅ Completed | 2 | AUTH-005 | P0 |
- Legacy line 4279: Done: AUTH-005                Create ProtectedRoute component (requires auth) [P0; Phase 4; completed 2026-09-18]
- Legacy line 4626: **Dependencies:** AUTH-005; reuses AUTH-004 sanitized role and AUTH-021 verified bootstrap.
- Legacy line 4633: - [x] Anonymous sessions retain fixed User/Admin login redirects; authenticated USER can enter only User routes and ADMIN only Admin routes. — Actual router/store, both-role direct/deep/index and all 20 declared private route denial cases PASS; AUTH-005 regression preserved.
- Legacy line 4705: introduced. AUTH-005's \`state.from\` stays descriptive and is not consumed. USER readiness/onboarding
- Legacy line 4891: baseline formatter discrepancies do not fail required CI gates. AUTH-005/006 and role-specific
