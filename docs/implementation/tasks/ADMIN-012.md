# ADMIN-012

**Control-plane status:** DONE / PRESERVED
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-004, BE-013

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 9101-9123

### 28.6 ADMIN-012 completion record

- **Task ID / Status:** `ADMIN-012` — **DONE — 2026-10-03**; implementation commit `a9a7b2a`,
  mobile-overflow fix `43feb4e`.
- **Delivered behavior:** `/admin/users` renders the real reusable DataTable with strict allowlisted
  DTO parsing, debounced backend search, server pagination/page-size controls, deterministic
  out-of-range recovery and distinct loading/empty/no-results/error/retry states. Private React Query
  keys are cleared on logout/account changes; EN/DE copy and direct-route refresh are supported.
- **Backend/security boundary:** reuse the completed BE-013 `GET /api/admin/users` contract without a
  backend change. Staging confirms ADMIN access, USER 403 and anonymous 401, all with no-store
  behavior; logout returns `/api/auth/me` to 401, removes the Admin table, and protected-route reopen
  renders no stale user records.
- **Verification:** focused Admin User/layout coverage passed 32 tests and the full frontend suite
  passed 74 files / 701 tests. TypeScript, ESLint, Prettier, production build and `git diff --check`
  passed. The previously accepted BE-013 focused suite remains 12/12 passing.
- **Staging acceptance:** bundle `index-D4iD9lXp.js` passed real-data load, search, page-size controls,
  refresh, EN/DE, empty/error automation coverage, clean console and desktop/tablet/mobile checks.
  At 375×812 the document has no horizontal overflow; the wide table remains in its own focusable
  horizontal scroller and search, pagination and Admin navigation remain usable.
- **Scope boundary / next task:** `ADMIN-013` remains **NOT STARTED**. `ACCEPT-001` remains blocked and
  was not resumed. The next authorized task is `ADMIN-013 — Create User detail view (profile, match
  status, activity)`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1418: | ADMIN-012 | Create Admin User Management page (DataTable) — ✅ Completed | 3 | ADMIN-004, BE-013 | P0 |
- Legacy line 1419: | ADMIN-013 | Create User detail view (profile, match status, activity) — ✅ Completed | 2 | ADMIN-012 | P0 |
- Legacy line 4348: Done: ADMIN-012               Create Admin User Management page (DataTable) [P0; Phase 11; completed 2026-10-03]
- Legacy line 9128:   linked from the ADMIN-012 table with accessible View details and Back actions. It renders strict
