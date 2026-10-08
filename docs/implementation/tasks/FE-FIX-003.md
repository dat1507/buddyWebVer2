# FE-FIX-003

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P1
**Dependencies (latest extracted):** FE-FIX-002

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 1873-1884

#### FE-FIX-003 — Language Flag SVG IDs

**Status**: Completed (✅)

- Ensure multiple flag instances cannot create duplicate DOM IDs.
- Preserve the current flag appearance in desktop and mobile variants.

**Implementation Notes**:
- Removed the fixed `uk-flag-clip` definition and its URL reference from `UkFlag`, eliminating the collision rather than introducing runtime-generated IDs.
- The SVG now clips through its existing rounded, `overflow-hidden` outer element while retaining the same viewBox and flag geometry.
- Added a regression test that renders multiple UK flags and verifies that they introduce no IDs or clip paths.


## Cross-reference occurrences outside extracted headings

- Legacy line 1268: | FE-FIX-003 | Remove duplicate SVG IDs from language flag instances | FE-FIX-002 | P1 |
- Legacy line 4233: Done:    FE-FIX-003      Remove duplicate flag SVG IDs [completed 2026-09-10]
