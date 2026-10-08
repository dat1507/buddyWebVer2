# ADMIN-002

**Control-plane status:** DONE / PRESERVED
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-001 — DONE; source shell, tests and accepted Git/CI evidence verified.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 5019-5063

### ADMIN-002 — Create Admin Sidebar navigation (all 11 modules)

- **Task ID:** `ADMIN-002`
- **Status:** Completed — 2026-09-19; **Priority:** P0; **Phase:** 7; **Cx:** 2
- **Dependencies:** ADMIN-001 — DONE; source shell, tests and accepted Git/CI evidence verified.
- **Goal/scope:** Deliver the eleven module destinations defined in Part 20 inside the existing guarded AdminLayout. Existing ten destinations were scaffolds; the canonical Event Sliders scaffold was missing.

**Definition of Done / acceptance derived from the registry scope and Part 20:**

- [x] All eleven localized native links: Overview, Users, Matching, Events, Event Sliders, Announcements, Knowledge Base, Campus, Analytics, Audit Log and Settings.
- [x] Canonical URLs share one route/navigation registry; the new `/admin/event-sliders` scaffold remains inside the existing ADMIN guard. Existing paths/titles are preserved; scaffold status is visible, with no business completion claim.
- [x] Exact Overview and segment-safe nested module matching, query/hash-independent selection, one `aria-current="page"`, decorative icons, visible keyboard focus and native Tab/Enter navigation.
- [x] EN/DE switching preserves route/session/content identity. Narrow stacked, `sm` two-column and `md` sidebar navigation fit available width. Short desktop sidebar scroll keeps the last link keyboard reachable; skip-to-main still works.
- [x] Unknown/loading/anonymous/USER access cannot expose the menu. Authoritative bootstrap and logout remain intact. Required regression, CI/security gates, actual browser/API/PostgreSQL, diff and credential review pass.

**Implementation:** `admin-routes.ts` owns canonical module descriptors, used by App and the new
`AdminSidebarNavigation`. Existing button variants, Typography, icons and EN/DE resources are reused.
AdminLayout adds the menu below its identity/toggle and bounds desktop sidebar height with scrolling.
No API/session/auth/cache implementation, backend, dependencies or environment files are changed.
The Event Sliders URL is defined by Part 20; its addition supplies guarded routing infrastructure,
not ADMIN-SLIDER CRUD, image upload, publication or ordering.

**Verification (2026-09-19):** 26 dedicated ADMIN-002 PASS; ADMIN-001 14 PASS; full frontend
394 PASS in 33 files with two workers. Format/lint/typecheck/build PASS; production npm audit zero
vulnerabilities. Initial high-concurrency execution hit two old login timeouts; no auth test changes
were needed for the passing complete rerun. Backend 381 PASS / 13 opt-in live SKIP plus three
PostgreSQL live PASS. Ruff, strict mypy, pip check, Alembic graph, package build, strict lockfile
pip-audit and Compose PASS. Local Compose config-read and pytest cache-write warnings are non-failing.
Actual browser/API/least-privilege PostgreSQL login, all eleven links, deep-link reload, EN/DE,
1280px/768px/640px/320px width fit, 1280×500 sidebar keyboard scrolling, skip-main focus, CSRF logout
and denied re-entry PASS; error console empty. Temporary tab/viewport/listeners cleaned up.

**Git workflow:** Implement/commit/normal push directly on main after gates/diff/secret review;
verify exact live SHA, Frontend/Backend CI and clean/synced working tree. No branch or deployment.

**Completion accounting:** Same 160 task IDs, fixed weights/partial-credit bounds and release rubric
as FE-021/FE-022/ADMIN-001. Only ADMIN-002 weight 2 moves NOT STARTED `[0, 0, 0]` to DONE `[1, 1, 1]`.
No module business, security/integration or deployment credit is added by navigation.

**Next development task after ADMIN-002:** ADMIN-003 — Create Admin Dashboard overview page (stats cards placeholder),
P0; dependency ADMIN-001 DONE, READY. Do not implement it unless explicitly requested.

**Out of Scope:** ADMIN-003 stats; data tables/dialogs; module CRUD/domain APIs; sliders content,
profile/readiness/onboarding/matching; AUTH-020 production operator gate; deployment.


## Cross-reference occurrences outside extracted headings

- Legacy line 1345: | ADMIN-002 | Create Admin Sidebar navigation (all 11 modules) — ✅ Completed | 2 | ADMIN-001 | P0 |
- Legacy line 4286: Done: ADMIN-002               Create Admin Sidebar navigation (all 11 modules) [P0; Phase 7; verified 2026-09-19]
- Legacy line 4983: - **Goal/scope:** Deliver the Admin sidebar/content shell described by Phase 7 and Part 20. The existing routed Outlet wrapper was partial; module navigation is ADMIN-002 and overview stats are ADMIN-003.
- Legacy line 5013: **Next development task after ADMIN-001:** ADMIN-002 — Create Admin Sidebar navigation (all 11 modules), P0;
- Legacy line 5014: dependency ADMIN-001 is DONE. Do not execute ADMIN-002 unless explicitly requested.
- Legacy line 5016: **Out of Scope:** ADMIN-002 module links, ADMIN-003 stats, tables/dialogs, domain APIs, profile,
- Legacy line 5068: - **Dependencies:** ADMIN-001 — DONE; guarded shell, tests and accepted Git/CI evidence verified. ADMIN-002 is also already on main but is not a declared dependency.
