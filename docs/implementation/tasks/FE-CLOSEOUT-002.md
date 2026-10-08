# FE-CLOSEOUT-002

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P0
**Dependencies (latest extracted):** FE-CLOSEOUT-001

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2062-2075

#### FE-CLOSEOUT-002 — Isolate Modal Background Content

**Status**: Completed (✅)

- Prevent content outside the mobile navigation drawer and Demo Video dialog from remaining available to keyboard or assistive-technology navigation while either modal is open.
- Preserve the existing Escape handling, focus containment and return, backdrop behavior, body scroll locking, localization, and responsive presentation.

**Implementation Notes**:
- Added reusable `useModalIsolation` behavior that applies both `inert` and `aria-hidden="true"` to content outside the active modal and restores each element's previous attributes during cleanup.
- Applied the shared behavior to the inline mobile navigation overlay and the portal-based Demo Video dialog without changing their public component contracts.
- Extended Navbar and Demo dialog tests to prevent background-isolation and cleanup regressions.
- Browser verification confirmed the Landing content is isolated while each modal is open, attributes are removed on close, and focus returns to the original trigger.
- Prettier, ESLint, strict type-check, all 76 tests, and production build pass; scroll-to-top test-environment warnings remain assigned to the next closeout task.


## Cross-reference occurrences outside extracted headings

- Legacy line 1301: | FE-CLOSEOUT-002 | Isolate modal background content from assistive technology | FE-CLOSEOUT-001 | P0 |
- Legacy line 1302: | FE-CLOSEOUT-003 | Finalize public route scroll restoration | FE-CLOSEOUT-002 | P0 |
- Legacy line 4249: Done:    FE-CLOSEOUT-002    Isolate modal background content [completed 2026-09-11]
