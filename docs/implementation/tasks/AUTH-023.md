# AUTH-023

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-021, AUTH-006 (complete on this branch).

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 4713-4761

### AUTH-023 — Implement Admin login role check, cleanup and redirect

**Task ID:** `AUTH-023`
**Status:** COMPLETED (✅) on 2026-09-18; **Priority:** P0; **Phase:** 5
**Dependencies:** AUTH-021, AUTH-006 (complete on this branch).
**Scope:** `/adminLogin` uses the shared login endpoint and verifies actual ADMIN role before identity installation.

The registry supplies title/dependencies only. Operational checks derive from AUTH-ARCH-001,
the sanitized response contract, PART 22 and its explicit newly issued USER-session logout rule:

- [x] Validated ADMIN login routes to `/admin/dashboard` with history replacement; no caller input chooses role/destination and no expected-role field is sent to the backend. — Actual client/store/StrictMode router ADMIN EN/DE held-response, sanitized projection, body/CSRF/cookie request, spoofed destination/storage and Back checks PASS.
- [x] Successful USER login never installs authenticated identity or mounts private UI; session-bound CSRF logout revokes the newly issued session before denial/redirect to `/`, with fixed accessible EN/DE notice and cleared password. — Held logout/store subscription/private-layout absence, exact session-CSRF request, EN/DE public notice/password/history PASS; real browser logout and anonymous private-route re-entry PASS.
- [x] Failed revocation stays locally unauthenticated and redirects with denial plus safe logout error/manual retry; one bounded CSRF recovery/retry, no false claim of server revocation. — Service/network cleanup failures and manual logout retry without credential resubmission; 403 recovered retry success and repeated rejection bounded at one retry PASS.
- [x] Existing verified ADMIN and recovered final `/me` ADMIN redirect to the fixed dashboard; existing verified USER redirects to public denial without revoking a previously established valid session. Unknown/loading/anonymous/malformed/error states do not trigger success routing. — Both verified roles, statuses, final `/me` hold, expired-access interim ADMIN/final USER, invalid role/ID and real browser recovered entries PASS.
- [x] Validation/focus, pending/duplicate protection, safe API/network errors/manual retry, unmount and superseding intents remain safe; private cache clears while public cache remains. — Existing form checks, API 401/403/422/429/503 and DE network, both roles unmounted completion, new login/logout superseding held cleanup, signout→Admin cookie ordering/private-public cache PASS.
- [x] Focused/full regression, frontend/backend quality/security gates, Git review and real local browser cookie/database acceptance pass; no transport/storage/backend/schema/env/dependency changes. — 34 dedicated AUTH-023, full frontend 321 PASS; backend 384 PASS/10 explicit opt-in Redis live SKIP; quality/audit and local acceptance PASS.

**Workspace/Git preflight:** Default cwd, writable root and Git root are
`C:\Users\phuoc\Downloads\buddyWebVer2`, writable YES. Clean `codex/auth-022` at
`9767a2f` supplies the verified prerequisites; `codex/auth-023` branches directly from it.
Remote: `https://github.com/dat1507/buddyWebVer2.git`. No reset/discard/merge.

**Implementation:** Shared client adds a frontend-only required ADMIN option and a sanitized
denial error carrying nullable safe cleanup failure. Role validation precedes identity installation;
internal session-CSRF logout stays in the same cookie queue and cannot deadlock through public logout.
Cleanup errors use existing global logout retry on the public page. The form uses primitive store
selectors/fixed redirects and clears its captured password after handled success/denial even if
detached. Landing renders only a whitelisted localized notice. AUTH-021 integration/Admin unit
tests updated; new actual client/store/router flow suite supplies the acceptance evidence.

**Verification:** Full frontend **321 PASS**, dedicated **34 PASS**, and post-type-syntax fix
client/User/Admin focused regression **96 PASS**. Prettier/ESLint/strict TypeScript/build PASS;
existing bundle above 500 kB is advisory. Full backend **384 PASS / 10 opt-in Redis live SKIP**,
including three isolated PostgreSQL cases; Ruff/strict mypy (57 files)/pip check/single Alembic head
PASS. Production npm audit zero vulnerabilities; strict pip-audit of fully pinned runtime
`requirements.lock` with `--no-deps --disable-pip` reports no known vulnerabilities. No local editable
package/dependency skip, env/config/dependency/generated/lab file in Git scope.
Real browser/API/isolated PostgreSQL acceptance: ADMIN login and recovered `/adminLogin` redirect,
new USER login denial/logout EN/DE, anonymous private-route re-entry after cleanup, valid User login
and previously established USER denial/session retention PASS. Browser error console empty.
Git diff/credential-signature review PASS. No production deployment or complete business dashboard claim.

Existing verified USER entry retention follows AUTH-006's public denial policy; the plan's explicit
logout applies to a newly issued USER login session. JWTs stay HttpOnly-only, CSRF stays memory-only,
backend current-role authorization remains independent. Copied-access TTL and AUTH-020 production
operator gate remain. Readiness/onboarding is FE-038; dashboard/layout pages remain scaffolding.

**Next development task after completion:** FE-021 — UserLayout; not started by AUTH-023.


## Cross-reference occurrences outside extracted headings

- Legacy line 1287: > **Approved UI-first exception**: AUTH-001, AUTH-002, and AUTH-003 are implemented as UI-only pages before Backend Foundation. They may include responsive layouts, accessible forms, client-side validation, and loading/error presentation contracts, but must not simulate successful authentication, create fake tokens, or perform fake role redirects. Backend connectivity remains exclusively in AUTH-021 through AUTH-023.
- Legacy line 1327: | AUTH-023 | Implement admin login flow: Admin login → role=ADMIN check → redirect — ✅ Completed | 2 | AUTH-021, AUTH-006 | P0 |
- Legacy line 1376: | FE-038 | Integrate onboarding routing and readiness gate — ✅ Completed | 2 | AUTH-022, AUTH-023, BE-016, FE-027 | P0 |
- Legacy line 1832: - AUTH-001, AUTH-002, and AUTH-003 may be completed as UI-only pages before Backend Foundation. API authentication, JWT persistence, role redirects, and protected-route behavior remain deferred to AUTH-021 through AUTH-023.
- Legacy line 3320:   expected role; AUTH-022/AUTH-023 route from the returned persisted role, while future protected
- Legacy line 4282: Done: AUTH-023                Implement admin login flow: Admin login → role=ADMIN check → redirect [P0; Phase 5; completed 2026-09-18]
- Legacy line 4708: link to \`/adminLogin\` is added. That surface's role check, logout/denial remains AUTH-023.
- Legacy line 4711: **Next development task:** AUTH-023 — Admin login role check, cleanup and redirect; not started by AUTH-022.
- Legacy line 5787: Cx2; dependencies AUTH-022, AUTH-023, BE-016 and FE-027 DONE, READY. It is not implemented here.
- Legacy line 5796: **Dependencies:** AUTH-022, AUTH-023, BE-016, FE-027
