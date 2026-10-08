# FE-CLOSEOUT-003

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P0
**Dependencies (latest extracted):** FE-CLOSEOUT-002

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2076-2091

#### FE-CLOSEOUT-003 — Finalize Public Route Scroll Restoration

**Status**: Completed (✅)

- Reset the browser scroll position to the top whenever the public route pathname changes, including `/login`, `/register`, and `/adminLogin`.
- Preserve hash-only navigation within the same pathname so Landing page anchor links continue to control their own scroll behavior.
- Add deterministic regression coverage without relying on jsdom's unimplemented native `window.scrollTo` behavior.

**Implementation Notes**:
- Added the reusable `useScrollToTop` hook and mounted it once in `PublicLayout`, covering every current and future public child route through the shared router boundary.
- Scoped the effect to `location.pathname`; query-string or hash-only changes do not cause an unintended jump to the top.
- Added four regression tests covering all three auth path transitions and the same-path hash-navigation exception.
- Added a test-environment `window.scrollTo` mock, removing the previous jsdom warning while keeping calls directly assertable.
- Browser verification confirmed `/ → /register → /login` route transitions reset `scrollY` to `0`, `/adminLogin` opens at the top, and no console error is emitted.
- Prettier, ESLint, strict type-check, all 80 tests, and production build pass. The existing Vite chunk-size advisory remains deferred and is unrelated to scroll restoration.


## Cross-reference occurrences outside extracted headings

- Legacy line 1302: | FE-CLOSEOUT-003 | Finalize public route scroll restoration | FE-CLOSEOUT-002 | P0 |
- Legacy line 1303: | FE-HYGIENE-002 | Verify pending auth layout changes and restore a clean working tree | FE-CLOSEOUT-003 | P0 |
- Legacy line 4250: Done:    FE-CLOSEOUT-003    Finalize public route scroll restoration [completed 2026-09-11]
