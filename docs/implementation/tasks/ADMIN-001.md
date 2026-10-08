# ADMIN-001

**Control-plane status:** DONE / PRESERVED
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** FE-005, AUTH-006 — both DONE; shared Card/Typography/buttons and actual ADMIN RoleGuard acceptance verified.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 4978-5018

### ADMIN-001 — Create AdminLayout component (sidebar + content) — clean, data-dense

- **Task ID:** `ADMIN-001`
- **Status:** Completed — 2026-09-18; **Priority:** P0; **Phase:** 7; **Cx:** 3
- **Dependencies:** FE-005, AUTH-006 — both DONE; shared Card/Typography/buttons and actual ADMIN RoleGuard acceptance verified.
- **Goal/scope:** Deliver the Admin sidebar/content shell described by Phase 7 and Part 20. The existing routed Outlet wrapper was partial; module navigation is ADMIN-002 and overview stats are ADMIN-003.

**Definition of Done / acceptance derived from the existing shell scope and Part 20 design principles:**

- [x] Compact sidebar/content shell distinguishes the Admin area using existing VGU branding, a dark sidebar and localized Admin badge; shared UI primitives are reused.
- [x] Existing nested `/admin/*` routes render inside the content Outlet without route/guard changes. AdminLayout owns one named main; private placeholders do not add another main. Public page and USER layout acceptance remain intact.
- [x] Desktop/tablet two-column layout and narrow-screen stacked regions fit their available widths; actual 1280px, 768px and 320px browser checks pass without horizontal overflow.
- [x] EN/DE named aside/main, unique skip-link target and keyboard skip-to-main/language toggle work. Existing bootstrap/final-me/refresh/CSRF/logout/role separation remain authoritative.

**Implementation:** 14rem sidebar and 96rem maximum-width shell, compact spacing, `minmax(0,1fr)`
content track, `md` breakpoint/sticky sidebar, wrapping narrow-screen controls and unique `useId`
main target. Card/Typography/LanguageToggle and the existing brand image are reused. RoutePlaceholder
uses a div for User/Admin content and retains a main for Public pages. App, guards, session client,
cache, token/persistence behavior, backend, dependency and environment files are unchanged.

**Verification (2026-09-18):** 14 dedicated ADMIN-001 PASS, FE-021/FE-022 33 PASS, full frontend
368 PASS. Format/lint/typecheck/build and production npm audit PASS (zero vulnerabilities).
Backend 381 PASS / 13 opt-in live SKIP; three additional PostgreSQL live cases PASS. Ruff, strict
mypy, pip check, Alembic graph, package build, strict runtime lockfile pip-audit and Compose PASS.
Actual local browser/API/least-privilege PostgreSQL Admin login, deep-link reload, desktop/tablet/
320px EN/DE, keyboard skip/toggle, logout and denied re-entry PASS; console errors absent. Ten Redis
live cases remain unconfigured. Existing bundle advisory and AUTH-020 production operator gate remain.

**Git workflow:** Implement/commit/normal push directly on main after gates, diff and secret review;
verify live remote SHA, CI and clean/synced working tree. No new task branch or deployment.

**Completion accounting:** Retain FE-021/FE-022 weights/rubric; ADMIN-001 weight 3 moves PARTIAL
credit `[0, .25, .5]` to DONE `[1, 1, 1]`. Best earned delta is 2.25, preserving prior scaffold credit.
No security/integration/deployment readiness credit is added for the shell.

**Next development task after ADMIN-001:** ADMIN-002 — Create Admin Sidebar navigation (all 11 modules), P0;
dependency ADMIN-001 is DONE. Do not execute ADMIN-002 unless explicitly requested.

**Out of Scope:** ADMIN-002 module links, ADMIN-003 stats, tables/dialogs, domain APIs, profile,
matching, events/sliders, onboarding and deployments.


## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1344: | ADMIN-001 | Create AdminLayout component (sidebar + content) — clean, data-dense — ✅ Completed | 3 | FE-005, AUTH-006 | P0 |
- Legacy line 1345: | ADMIN-002 | Create Admin Sidebar navigation (all 11 modules) — ✅ Completed | 2 | ADMIN-001 | P0 |
- Legacy line 1346: | ADMIN-003 | Create Admin Dashboard overview page (stats cards placeholder) — ✅ Completed | 2 | ADMIN-001 | P0 |
- Legacy line 4285: Done: ADMIN-001               Create AdminLayout component (sidebar + content) — clean, data-dense [P0; Phase 7; completed 2026-09-18]
- Legacy line 4973: **Next development task after FE-022 completion:** ADMIN-001 — AdminLayout, P0; dependencies FE-005 and AUTH-006 are DONE.
- Legacy line 4974: FE-023 still awaits BE-012, BE-016 and FE-038. ADMIN-001 is not started by FE-022.
- Legacy line 5023: - **Dependencies:** ADMIN-001 — DONE; source shell, tests and accepted Git/CI evidence verified.
- Legacy line 5041: **Verification (2026-09-19):** 26 dedicated ADMIN-002 PASS; ADMIN-001 14 PASS; full frontend
- Legacy line 5055: as FE-021/FE-022/ADMIN-001. Only ADMIN-002 weight 2 moves NOT STARTED \`[0, 0, 0]\` to DONE \`[1, 1, 1]\`.
- Legacy line 5059: P0; dependency ADMIN-001 DONE, READY. Do not implement it unless explicitly requested.
- Legacy line 5068: - **Dependencies:** ADMIN-001 — DONE; guarded shell, tests and accepted Git/CI evidence verified. ADMIN-002 is also already on main but is not a declared dependency.
- Legacy line 5087: **Verification (2026-09-19):** 17 dedicated ADMIN-003 PASS; ADMIN-001/002 regression 40 PASS; full
- Legacy line 5108: as FE-021/FE-022/ADMIN-001/002. Only ADMIN-003 weight 2 moves NOT STARTED \`[0, 0, 0]\` to DONE
