# AUTH-006

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-005; reuses AUTH-004 sanitized role and AUTH-021 verified bootstrap.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 4622-4663

### AUTH-006 — Create RoleGuard component (requires specific role)

**Task ID:** `AUTH-006`
**Status:** COMPLETED (✅) on 2026-09-18; **Priority:** P0; **Phase:** 4
**Dependencies:** AUTH-005; reuses AUTH-004 sanitized role and AUTH-021 verified bootstrap.
**Goal:** Prevent rendering private route descendants for a verified session with the wrong role.

The registry has no separate detailed AC. Operational checks below derive from its specific-role
requirement, AUTH-ARCH-001 pending contract and PART 22 authorization layering:

- [x] Unknown/loading delegate to ProtectedRoute's accessible neutral EN/DE pending, retain URL and never mount private descendants. — Both roles/statuses, localized pending and private mount checks PASS.
- [x] Anonymous sessions retain fixed User/Admin login redirects; authenticated USER can enter only User routes and ADMIN only Admin routes. — Actual router/store, both-role direct/deep/index and all 20 declared private route denial cases PASS; AUTH-005 regression preserved.
- [x] Wrong-role requests replace history with fixed public `/`, never mount private layout/children, never follow caller-supplied destinations and preserve the valid session. — Child-effect, history/Back, query/hash, unchanged identity and no-network checks PASS.
- [x] Verified role changes and session clear/re-verification immediately remove incompatible private content; bootstrap waits for final `/me`, with bounded refresh/retry and existing private-cache clearing. — StrictMode held `/me`, refresh versus final `/me` role, both refresh role transitions/private-public cache, malformed role fail-closed tests PASS.
- [x] Focused/router/client integration, real local browser cookies/database, regression and quality/security gates pass. Backend role checks remain authoritative; no credentials/persistence/network added to the guard. — 50 focused and full frontend 256 PASS; backend 384 PASS/10 existing opt-in Redis live SKIP; quality/dependency/credential checks PASS.

**Implementation:** Added reusable typed `features/auth/role-guard.tsx`, two colocated test files
and exact USER/ADMIN guards in App. Non-authenticated states reuse ProtectedRoute directly; role
selectors subscribe to sanitized verified identity. Wrong role redirects with replacement to `/`
without logout or destination state. No change to API/bootstrap/CSRF/cookies/store/backend schema.

**Verification:** Frontend format/lint/strict typecheck/production build PASS (existing >500 kB
chunk advisory). Backend Ruff/strict mypy (57 files)/pip check PASS; three PostgreSQL live cases
enabled in full regression. Production npm audit: zero vulnerabilities. Strict pip-audit: all 77
pinned external installed distributions, no known vulnerabilities. Environment-wide strict audit
rejects the local editable `vgu-buddy-api` source (not published on PyPI), so excluded editable
source via a pinned external-only audit input in the ignored disposable lab; no dependency change
or external dependency skip. Repository source is covered by regression/static/security review.
Git diff/credential-signature review PASS; no env/config/dependency, generated or lab files in Git.
Real browser + isolated PostgreSQL: anonymous Admin redirect, USER/ADMIN login, matching deep-link
reload retaining query/hash, both cross-role denials to public home retaining sessions, both index
routes, EN/DE, immediate logout and denied re-entry PASS. Browser error console empty. Acceptance
is local only; no deployed production authorization or completed business-page claim.

**Scope:** RoleGuard and existing route integration, focused tests and implementation evidence.
Login form role checks, success redirects and wrong-role Admin-login cleanup remain AUTH-022/023.
Existing User/Admin placeholder layouts/pages stay scaffolding. No backend/API/schema change or
production deployment. The wrong-role destination is public `/`, which avoids login or role loops;
direct navigation denial does not log out an otherwise valid session.

**Next development task:** AUTH-022 — User login role check and redirect; not started by AUTH-006.


## Cross-reference occurrences outside extracted headings

- Legacy line 1284: | AUTH-006 | Create RoleGuard component (requires specific role) — ✅ Completed | 2 | AUTH-005 | P0 |
- Legacy line 1326: | AUTH-022 | Implement login flow: User login → role check → redirect — ✅ Completed | 2 | AUTH-021, AUTH-006 | P0 |
- Legacy line 1327: | AUTH-023 | Implement admin login flow: Admin login → role=ADMIN check → redirect — ✅ Completed | 2 | AUTH-021, AUTH-006 | P0 |
- Legacy line 1335: | FE-021 | Create UserLayout component (sidebar + content area) — ✅ Completed | 3 | FE-005, AUTH-006 | P0 |
- Legacy line 1344: | ADMIN-001 | Create AdminLayout component (sidebar + content) — clean, data-dense — ✅ Completed | 3 | FE-005, AUTH-006 | P0 |
- Legacy line 4280: Done: AUTH-006                Create RoleGuard component (requires specific role) [P0; Phase 4; completed 2026-09-18]
- Legacy line 4616: **Out of Scope:** AUTH-006 role isolation, AUTH-022/023 login role checks/redirects, layout/profile
- Legacy line 4620: **Next development task:** AUTH-006 — RoleGuard; not started by AUTH-005.
- Legacy line 4668: **Dependencies:** AUTH-021, AUTH-006 (complete on this branch).
- Legacy line 4717: **Dependencies:** AUTH-021, AUTH-006 (complete on this branch).
- Legacy line 4755: Existing verified USER entry retention follows AUTH-006's public denial policy; the plan's explicit
- Legacy line 4900: - **Dependencies:** FE-005, AUTH-006
- Legacy line 4973: **Next development task after FE-022 completion:** ADMIN-001 — AdminLayout, P0; dependencies FE-005 and AUTH-006 are DONE.
- Legacy line 4982: - **Dependencies:** FE-005, AUTH-006 — both DONE; shared Card/Typography/buttons and actual ADMIN RoleGuard acceptance verified.
