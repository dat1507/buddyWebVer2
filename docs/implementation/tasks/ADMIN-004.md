# ADMIN-004

**Control-plane status:** DONE / PRESERVED
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** FE-005 — DONE; design-system Button/Card/Typography/theme source and existing regression evidence verified. FE-004 shadcn configuration/Radix Slot is also present but is not a declared dependency.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 5119-5174

### ADMIN-004 — Create reusable DataTable component (sort, filter, search, pagination)

- **Task ID:** `ADMIN-004`
- **Status:** Completed — 2026-09-19; **Priority:** P0; **Phase:** 7; **Cx:** 4
- **Dependencies:** FE-005 — DONE; design-system Button/Card/Typography/theme source and existing regression evidence verified. FE-004 shadcn configuration/Radix Slot is also present but is not a declared dependency.
- **Goal/scope:** Reusable table infrastructure for complete bounded caller-owned client datasets. Part 16 defines the four required capabilities; Part 24 defines execution order. This task had no extended DoD before this derived acceptance record. Domain lists and server APIs/pagination belong to subsequent module tasks.

**Definition of Done / acceptance derived from the registry scope and existing design conventions:**

- [x] Generic typed data/column descriptors and stable row/column IDs; plain accessors, custom cells/actions, opt-out search, canonical filter values and custom comparator support.
- [x] Non-mutating global search plus AND exact column filters before stable locale-aware string/numeric sort and pagination. Single-column ascending/descending/source-order cycle; built-in missing values remain last in both directions.
- [x] Configurable valid page sizes, correct filtered totals/ranges and bounded Previous/Next. Search/filter/sort/page-size changes reset to page one; dataset/options shrink clamps page state without resurrecting stale out-of-range state.
- [x] EN/DE built-in controls/states, labels and announcements; caller-localized headers/options/cells/caption/public error. Locale changes retain view state with stable IDs.
- [x] Native table/caption/scoped headers, native labeled controls and instance-unique IDs, one active aria-sort and visible focus. Named focusable table scroller contains mobile overflow and allows off-screen cell actions to be reached by keyboard.
- [x] Caller-driven loading/error/optional retry/empty/no-results states hide stale rows/totals. No fabricated data, stats, fetch, API route, storage or automatic retry.
- [x] Meaningful processing/component tests, existing full regressions, required CI/security gates, isolated synthetic browser checks and diff/React/credential review pass.

**Implementation:** `data-table-model.ts` defines the public column/value/filter types and pure
processing; `data-table.tsx` owns view/paging state and native presentation. Existing Button/theme
tokens and `cn` are reused; no table-library dependency is added. Accessor text drives search;
custom React cell content is not introspected. Reset retains page size. Missing values, unsafe page
options, empty vs constrained results, multiple instances, stable custom-cell state and metadata/
data changes are covered. Server-side processing is deliberately outside this component contract.
No product route, backend/auth/session/cache/API/dependency/environment implementation changes.

**Verification (2026-09-19):** 27 dedicated ADMIN-004 PASS; full frontend 438 PASS / 37 files / two
workers, including previous ADMIN/auth/USER regressions. Format/lint/typecheck/production build PASS;
production npm audit zero vulnerabilities. Backend 381 PASS / 13 opt-in live SKIP; pip check, Ruff,
strict mypy (57 files), Alembic graph, package build, strict lockfile pip-audit and Compose PASS.
Live PostgreSQL/Redis cases are not rerun for this pure component scope; no fresh browser-to-auth-
API/database acceptance is claimed. Existing bundle advisory and local cache/config warnings remain.

Actual isolated browser harness outside Git imports the real component with 13 synthetic records.
Numeric sort by Enter, filter + cross-page case-insensitive search, reset/source order, EN↔DE state
retention, loading/error/retry/empty/no-results, data shrink/grow clamp, page size and custom action
PASS. EN/DE document width fits 1280/768/640/320px; the 512px table stays inside a focusable scroller
at mobile. Arrow keys scroll horizontally and Tab scrolls an off-screen action into view. Console
errors empty; tab, language/viewport override and owned server cleaned up. Review fixed sort-only
empty messaging and removed-page-size restoration; native Windows harness imports were corrected
outside Git. Final verification receipt records any setup findings and exact CI SHA.

**Git workflow:** Implement/commit/normal push directly on main after gates/diff/secret review;
verify live exact SHA, Frontend/Backend CI and clean/synced state in the external completion receipt.
No new task branch, force push, history rewrite or deployment.

**Completion accounting:** Keep all accepted 160 IDs, Cx/deps/priorities/weights, bounds and release
rubric. ADMIN-004 has three direct dependents, so its existing weight is Cx4 × P0 1 × acceptance 1 ×
fanout 1.15 = 4.6; only its credit moves NOT STARTED `[0,0,0]` → DONE `[1,1,1]`. No domain list/API,
matching, security or deployment credit. ADMIN-006/012/ADMIN-SLIDER-001 still need backend contracts.

**Next development task:** ADMIN-005 — Create reusable ConfirmDialog component, P0 / Phase7 / Cx1;
dependency FE-004 DONE, READY. It is not implemented here; do not execute unless explicitly requested.

**Out of Scope:** ConfirmDialog, domain Admin lists/CRUD/APIs, manual server pagination, auth, real
business stats/profile/readiness/onboarding/events/sliders/matching, production operator gate/deployment.


## Cross-reference occurrences outside extracted headings

- Legacy line 1347: | ADMIN-004 | Create reusable DataTable component (sort, filter, search, pagination) — ✅ Completed | 4 | FE-005 | P0 |
- Legacy line 1412: | ADMIN-006 | Create Admin Events list with editorial/time filters | 3 | ADMIN-004, EVT-006, EVT-009 | P0 |
- Legacy line 1418: | ADMIN-012 | Create Admin User Management page (DataTable) — ✅ Completed | 3 | ADMIN-004, BE-013 | P0 |
- Legacy line 1427: | ADMIN-SLIDER-001 | Create \`/admin/event-sliders\` list with status/visibility filters and loading/error/empty states | 3 | ADMIN-004, EVS-006 | P0 |
- Legacy line 4288: Done: ADMIN-004               Create reusable DataTable component (sort, filter, search, pagination) [P0; Phase 7; verified 2026-09-19]
- Legacy line 5112: **Next development task after ADMIN-003:** ADMIN-004 — Create reusable DataTable component (sort, filter, search,
- Legacy line 5114: verified; ADMIN-004 is not implemented here. Do not execute it unless explicitly requested.
- Legacy line 6142: **Dependencies:** ADMIN-004, EVT-006, EVT-009
- Legacy line 8683: - **Dependencies:** \`ADMIN-004\`, \`EVT-006\`, \`EVT-009\`.
