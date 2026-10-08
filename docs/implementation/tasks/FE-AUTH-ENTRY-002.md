# FE-AUTH-ENTRY-002

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P0
**Dependencies (latest extracted):** AUTH-001, AUTH-002

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2007-2019

#### FE-AUTH-ENTRY-002 — Mobile User Auth Discovery

**Status**: Completed (✅)

- Mobile exposes those two actions directly in the existing drawer.

**Implementation Notes**:
- Added direct User Login (`/login`) and Create Student Account (`/register`) links to the existing mobile drawer without introducing a nested menu.
- Both actions use internal React Router navigation, share the drawer's visible focus treatment, and close the drawer after selection.
- Preserved the existing dialog semantics, focus containment, Escape handling, focus return, scroll lock, language toggle, and public navigation items.
- Added vertical overflow handling for short mobile viewports so the expanded navigation remains usable.
- Confirmed through EN/DE tests that the mobile drawer contains both User actions and no `/adminLogin` link.


## Cross-reference occurrences outside extracted headings

- Legacy line 1296: | FE-AUTH-ENTRY-002 | Add direct User Login and Create Student Account actions to the mobile drawer | AUTH-001, AUTH-002 | P0 |
- Legacy line 2004: - Left the mobile drawer unchanged for FE-AUTH-ENTRY-002.
- Legacy line 4244: Done:    FE-AUTH-ENTRY-002  Add mobile User auth actions [completed 2026-09-11]
