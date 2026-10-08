# ADMIN-003

**Control-plane status:** DONE / PRESERVED
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-001 — DONE; guarded shell, tests and accepted Git/CI evidence verified. ADMIN-002 is also already on main but is not a declared dependency.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 5064-5118

### ADMIN-003 — Create Admin Dashboard overview page (stats cards placeholder)

- **Task ID:** `ADMIN-003`
- **Status:** Completed — 2026-09-19; **Priority:** P0; **Phase:** 7; **Cx:** 2
- **Dependencies:** ADMIN-001 — DONE; guarded shell, tests and accepted Git/CI evidence verified. ADMIN-002 is also already on main but is not a declared dependency.
- **Goal/scope:** Replace the Dashboard scaffold with the six stats-card placeholders defined in Part 20. Part 16 defines task scope and Part 24 defines execution order; no extended ADMIN-003 contract existed before this acceptance record.

**Definition of Done / acceptance derived from the registry scope and Part 20:**

- [x] Canonical `/admin/dashboard` renders the overview in the existing ADMIN guard/layout; `/admin` redirects there. Other ten module destinations remain scaffolds.
- [x] Total Users, Active Matches, Published Events, AI Queries Today, Unmatched Students and Upcoming Events have EN/DE labels and explicit unavailable values. No fabricated operational totals, plan illustration values, zero counts, stats requests or fake loading/error states.
- [x] Shared Card/Typography/icons, semantic definition list, localized page h1/named section and one main. Decorative icons/dashes are hidden from assistive technology; unavailable status remains accessible.
- [x] Responsive one/two/four-column grid and wrapping fit actual available desktop/tablet/mobile width in EN/DE. Native module links, current Overview selection, language switching and skip-to-main remain keyboard usable.
- [x] Unknown/loading/anonymous/USER states cannot expose the page. Authoritative final-me bootstrap, query/hash reload, session identity, logout/failed logout and denied re-entry remain intact.
- [x] Dedicated and regression tests, required CI/security gates, actual browser/API/PostgreSQL, diff/React/credential review pass.

**Implementation:** `AdminOverviewPage` uses static metric descriptors and localization, with no
session/store/query effects. The Admin route registry gains a page/placeholder union following
existing USER delivery metadata; App renders the overview component inside the unchanged ADMIN
boundary. Every value is a decorative em dash plus Not available/Nicht verfügbar, with an honest
page description. Labels/title wrap; grid columns are one below sm, two at sm and four at xl.
No auth/session/API/cache/backend implementation, dependencies or environment files change.

**Verification (2026-09-19):** 17 dedicated ADMIN-003 PASS; ADMIN-001/002 regression 40 PASS; full
frontend 411 PASS in 35 files with two workers. Format/lint/typecheck/production build PASS;
production npm audit zero vulnerabilities. Backend 381 PASS / 13 opt-in live SKIP plus three
separate PostgreSQL live PASS. Ruff, strict mypy (57 files), pip check, Alembic graph, package build,
strict lockfile pip-audit and Compose validation PASS. Ten Redis live cases remain unconfigured.
Local pytest cache-write, Docker config-read and existing >500kB bundle warnings are non-failing.

Actual browser/API/least-privilege PostgreSQL ADMIN login, six unavailable values, module navigation,
query/hash deep-link reload, native Enter language switching, 1280px/768px/640px/320px width fit,
skip-main focus, logout and denied re-entry PASS; console errors empty. German title initially
overflowed the 320px viewport (321px document vs 305px available); wrapping fixes measured fit to
305/305px. Two existing DE login assertions expected the former English scaffold title; they now
assert the localized h1 while retaining session/password/routing/history assertions. Full final
frontend gates were rerun with a saved log after earlier background handles disappeared. Temporary
tab/viewport cleaned up; listener inventory confirms zero active lab listeners.

**Git workflow:** Implement/commit/normal push directly on main after gates/diff/secret review;
verify exact live SHA, Frontend/Backend CI and clean/synced working tree in the external completion
receipt. No new task branch, force push, history rewrite or deployment.

**Completion accounting:** Same 160 task IDs, fixed weights/partial-credit bounds and release rubric
as FE-021/FE-022/ADMIN-001/002. Only ADMIN-003 weight 2 moves NOT STARTED `[0, 0, 0]` to DONE
`[1, 1, 1]`, earning 2 points. No layout/navigation double count or real stats, matching, module CRUD,
security/integration/deployment credit. ADMIN-014 still awaits MATCH-013.

**Next development task after ADMIN-003:** ADMIN-004 — Create reusable DataTable component (sort, filter, search,
pagination), P0 / Phase 7 / Cx 4; dependency FE-005 DONE, READY. Shared primitives and test evidence
verified; ADMIN-004 is not implemented here. Do not execute it unless explicitly requested.

**Out of Scope:** Real dashboard stats/APIs, module CRUD, data tables/dialogs, matching, profile/
readiness/onboarding/events/sliders, AUTH-020 production Redis/TLS/ingress operator gate and deployment.


## Cross-reference occurrences outside extracted headings

- Legacy line 1346: | ADMIN-003 | Create Admin Dashboard overview page (stats cards placeholder) — ✅ Completed | 2 | ADMIN-001 | P0 |
- Legacy line 1489: | ADMIN-014 | Create Admin Matching overview | 2 | ADMIN-003, MATCH-013 | P0 |
- Legacy line 4287: Done: ADMIN-003               Create Admin Dashboard overview page (stats cards placeholder) [P0; Phase 7; verified 2026-09-19]
- Legacy line 4983: - **Goal/scope:** Deliver the Admin sidebar/content shell described by Phase 7 and Part 20. The existing routed Outlet wrapper was partial; module navigation is ADMIN-002 and overview stats are ADMIN-003.
- Legacy line 5016: **Out of Scope:** ADMIN-002 module links, ADMIN-003 stats, tables/dialogs, domain APIs, profile,
- Legacy line 5058: **Next development task after ADMIN-002:** ADMIN-003 — Create Admin Dashboard overview page (stats cards placeholder),
- Legacy line 5061: **Out of Scope:** ADMIN-003 stats; data tables/dialogs; module CRUD/domain APIs; sliders content,
- Legacy line 6462: **Dependencies:** ADMIN-003, MATCH-013
- Legacy line 6884: | ADMIN-V2-002 (**Done 2026-10-02**) | Monitoring UI | ADMIN-V2-001, ADMIN-003/004 | No run/publish/override controls | UI/RBAC/a11y tests |
- Legacy line 7835: - **Dependencies / ownership:** ADMIN-V2-001, ADMIN-003/004; Frontend.
