# FE-EVENT-STATIC-001

**Control-plane status:** DONE / PRESERVED
**Track:** events
**Priority:** -
**Dependencies (latest extracted):** completed Landing/carousel foundation and the six audited project-owned posters.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 9063-9085

#### FE-EVENT-STATIC-001 — Restore static Upcoming Events for the current release

- **Task ID / Status:** `FE-EVENT-STATIC-001` — **DONE — IMPLEMENTED AND LOCALLY VERIFIED**, current
  release; P0.
- **Dependencies:** completed Landing/carousel foundation and the six audited project-owned posters.
- **Frontend changes:** canonical static asset folder; typed localized data module; props-driven
  `EventsSlider`; unconditional Landing placement; static empty state hides the section; future
  dynamic feature gate renamed and limited to User/Admin surfaces.
- **Backend/API/database/Storage/Admin changes:** none.
- **Click behavior:** promotional-only; no detail route or legacy-post link.
- **Acceptance Criteria / DoD:** six posters render in deterministic legacy order in EN/DE; controls,
  autoplay, focus/hover pause and reduced-motion behavior remain accessible; an empty array removes
  the entire section; no Event endpoint is requested; unrelated Landing/login/Admin entry behavior
  is unchanged; targeted/full tests, typecheck, lint, formatting, build and diff check pass.
- **Verification — 2026-10-03:** focused Event/Landing/config coverage passed 18 tests; the complete
  frontend suite passed 72 files / 685 tests after one timing-only test was rerun cleanly; TypeScript,
  ESLint, Prettier, production build and `git diff --check` passed. Local production-build browser
  smoke verified EN/DE content, carousel navigation, User/Admin login routes, zero console errors and
  zero `/api/events` or `/api/event-sliders` resource requests.
- **Deployment checkpoint:** verify the pushed SHA on frontend staging before current-release
  acceptance. That check neither enables the dynamic Event flag nor gives Part 27 completion credit.
- **Next Task:** complete remaining Admin/core staging acceptance, then `ACCEPT-001`.


## Cross-reference occurrences outside extracted headings

- Legacy line 9088: 1. \`FE-EVENT-STATIC-001\` — implement and verify the frontend-only Upcoming Events restoration.
