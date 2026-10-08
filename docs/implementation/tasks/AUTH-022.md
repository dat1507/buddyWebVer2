# AUTH-022

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-021, AUTH-006 (complete on this branch).

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 4664-4712

### AUTH-022 — Implement login flow: User login → role check → redirect

**Task ID:** `AUTH-022`
**Status:** COMPLETED (✅) on 2026-09-18; **Priority:** P0; **Phase:** 5
**Dependencies:** AUTH-021, AUTH-006 (complete on this branch).
**Scope:** Complete `/login` session-role routing using the existing credentialed CSRF login client.

The registry provides title/dependencies only. These operational checks derive from its role-check
requirement, AUTH-ARCH-001, the approved sanitized login response and PART 22 role-routing diagram:

- [x] Real login installs only validated sanitized identity; USER routes to `/user/dashboard`, ADMIN to `/admin/dashboard`, with history replacement and correct RoleGuard subtree. — Actual client/store/router EN/DE pending→response tests, payload projection, body/CSRF/credentials and Back checks PASS.
- [x] Existing verified sessions visiting `/login`, including recovered reload sessions, use the same fixed destinations; unknown/loading/anonymous and malformed/failed verification never trigger premature success routing. — Both roles, all non-authenticated statuses, four malformed identities, held final `/me` and expired-access final-role tests PASS.
- [x] Existing validation/focus, pending/duplicate-submit protection, safe EN/DE errors and manual retry remain; success clears password even if the form has detached. — Existing form validation/focus and new pending/duplicate/error/retry/EN-DE/attached-detached password checks PASS.
- [x] Query/hash/router state/stale storage cannot choose a destination or role; unmounted form completion, superseded login/logout and bootstrap responses cannot produce stale navigation or private content. — External/protocol-relative/wrong-subtree inputs, navigation away, logout versus held login, new login versus held bootstrap PASS.
- [x] Existing account-switch/logout/private-cache behavior, public cache, guards/forms/backend auth regression and quality/security gates pass, with actual local browser cookie/database acceptance. — Both account-switch role destinations/private-public cache tests, 31 dedicated AUTH-022 and full frontend 287 PASS; backend 384 PASS/10 explicit existing Redis live SKIP; local real cookie/database browser PASS.

**Implementation:** `UserLoginPage` uses primitive verified status/role selectors and fixed
declarative history-replacing redirects. Success no longer remains a notice on the login form.
The submitted password input is cleared after successful client login even if detached; errors
retain manual retry. AUTH-021 form integration and User-page tests updated for resulting routing;
new `features/auth/user-login-flow.test.tsx` covers actual singleton client/store/StrictMode router.
No change to API/session client/bootstrap/CSRF/cookies/store/backend/layout contracts.

**Workspace/Git preflight:** Default cwd, writable root and Git root are
`C:\Users\phuoc\Downloads\buddyWebVer2`; initial checkout was clean `main` at `636218a`.
Prerequisites were verified on pushed `codex/auth-006` at `d15bd58`; created `codex/auth-022` from
that existing commit without reset/discard/merge. Remote is `https://github.com/dat1507/buddyWebVer2.git`.

**Verification:** Full frontend **287 PASS**, format/ESLint/strict TypeScript/build PASS; the
existing chunk above 500 kB is advisory. Full backend **384 PASS / 10 opt-in live Redis SKIP**, including
three isolated PostgreSQL cases; Ruff/strict mypy (57 files)/pip check/Alembic single head PASS.
Production npm audit reports zero vulnerabilities. Strict runtime pip-audit against
`requirements.lock` with `--no-deps --disable-pip` (fully pinned transitive input) reports no known
vulnerabilities; no editable local-source or dependency skip. Git diff/credential signature review
PASS, with no env/config/dependency/generated/lab file change in Git scope.
Real browser + isolated PostgreSQL: actual USER login in DE, ADMIN via `/login` in EN, correct
dashboard roles, recovered sessions visiting `/login`, ignored redirect queries, dashboard reload,
logout and denied re-entry PASS. Browser error console empty. No fake successful auth/store role,
production deployment, complete dashboard/business-page or onboarding-readiness claim.

Fixed role destinations follow the current auth diagram; no unapproved return-to URL contract is
introduced. AUTH-005's `state.from` stays descriptive and is not consumed. USER readiness/onboarding
is FE-038 after its backend/UI prerequisites; AUTH-022 targets the existing dashboard scaffold.
ADMIN can use the shared `/login` endpoint and routes from its verified persisted role; no public
link to `/adminLogin` is added. That surface's role check, logout/denial remains AUTH-023.
No new API calls, auth transport/storage, backend/schema/env/dependency or production deployment.

**Next development task:** AUTH-023 — Admin login role check, cleanup and redirect; not started by AUTH-022.


## Cross-reference occurrences outside extracted headings

- Legacy line 1326: | AUTH-022 | Implement login flow: User login → role check → redirect — ✅ Completed | 2 | AUTH-021, AUTH-006 | P0 |
- Legacy line 1376: | FE-038 | Integrate onboarding routing and readiness gate — ✅ Completed | 2 | AUTH-022, AUTH-023, BE-016, FE-027 | P0 |
- Legacy line 3320:   expected role; AUTH-022/AUTH-023 route from the returned persisted role, while future protected
- Legacy line 4281: Done: AUTH-022                Implement login flow: User login → role check → redirect [P0; Phase 5; completed 2026-09-18]
- Legacy line 4616: **Out of Scope:** AUTH-006 role isolation, AUTH-022/023 login role checks/redirects, layout/profile
- Legacy line 4657: Login form role checks, success redirects and wrong-role Admin-login cleanup remain AUTH-022/023.
- Legacy line 4662: **Next development task:** AUTH-022 — User login role check and redirect; not started by AUTH-006.
- Legacy line 4892: redirects/denial in AUTH-022/023 are not implemented here.
- Legacy line 5787: Cx2; dependencies AUTH-022, AUTH-023, BE-016 and FE-027 DONE, READY. It is not implemented here.
- Legacy line 5796: **Dependencies:** AUTH-022, AUTH-023, BE-016, FE-027
