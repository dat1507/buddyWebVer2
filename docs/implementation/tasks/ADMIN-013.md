# ADMIN-013

**Control-plane status:** DONE / PRESERVED
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-012

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 9124-9150

### 28.7 ADMIN-013 completion record

- **Task ID / Status:** `ADMIN-013` — **DONE — 2026-10-04**; implementation commit `8775dfb`.
- **Delivered behavior:** `/admin/users/:userId` is a direct-refresh-safe, read-only detail route
  linked from the ADMIN-012 table with accessible View details and Back actions. It renders strict
  allowlisted account/profile fields, verified/account state, authoritative Buddy count/status,
  onboarding/account milestones and only the matching-safe preferred activities. Localized
  loading, safe 404, error and retry states are included; no user mutation control was added.
- **Backend/security boundary:** reused audited BE-013 `GET /api/admin/users/:id` plus existing
  ADMIN-only `GET /api/admin/matching/participants/:profile_id?locale=...`; no backend change or
  migration. Both queries use private React Query keys and the existing logout/account-switch cache
  clearing. The route stays inside the ADMIN RoleGuard; focused USER/anonymous guard and BE-013 RBAC
  regressions pass.
- **Verification:** focused frontend coverage passed 5 files / 55 tests; the full frontend suite
  passed 75 files / 716 tests. TypeScript, full ESLint, full Prettier, production build and
  `git diff --check` passed. Focused BE-013/Admin matching backend coverage passed 32/32.
- **Staging acceptance:** bundle `index-D4iCIW3e.js` passed list-to-detail and Back navigation with a
  real existing user, direct refresh, safe 404, EN/DE, clean console and ADMIN detail/matching API
  responses at 200. The detail showed the coordinator-safe profile, one active Buddy relationship
  and localized activity labels. A 375 px mobile override produced a single-column card grid with no
  document-level horizontal overflow. Logout removed all visible detail, protected-route reopen
  returned to `/adminLogin`, and the live detail API returned anonymous 401 with `no-store`; the
  unchanged BE-013 USER 403 boundary remains covered by its accepted contract and focused regression.
- **Scope boundary / next task:** `ACCEPT-001` remains **BLOCKED** and was not resumed. The next
  authorized work is to resume its remaining staging acceptance gates; no production deployment was
  performed.


## Cross-reference occurrences outside extracted headings

- Legacy line 1419: | ADMIN-013 | Create User detail view (profile, match status, activity) — ✅ Completed | 2 | ADMIN-012 | P0 |
- Legacy line 4349: Done: ADMIN-013               Create User detail view (profile, match status, activity) [P0; Phase 11; completed 2026-10-04]
- Legacy line 9120: - **Scope boundary / next task:** \`ADMIN-013\` remains **NOT STARTED**. \`ACCEPT-001\` remains blocked and
- Legacy line 9121:   was not resumed. The next authorized task is \`ADMIN-013 — Create User detail view (profile, match
