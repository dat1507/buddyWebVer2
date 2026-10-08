# FE-AUTH-ENTRY-001

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P0
**Dependencies (latest extracted):** AUTH-001, AUTH-002

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 1993-2006

#### FE-AUTH-ENTRY-001 — Desktop User Auth Discovery

**Status**: Completed (✅)

- Desktop uses one compact `Sign in` trigger so the header is not overloaded.
- Its menu contains only User Login and Create Student Account.

**Implementation Notes**:
- Added a desktop-only localized `Sign in` disclosure to the existing Navbar action area, adjacent to the language toggle.
- The disclosure exposes exactly two internal routes: User Login (`/login`) and Create Student Account (`/register`). It contains no Admin Login entry.
- Added `aria-expanded`, `aria-controls`, a localized navigation label, Escape-to-close with focus return, outside-click dismissal, visible focus states, and close-on-selection behavior.
- Left the mobile drawer unchanged for FE-AUTH-ENTRY-002.
- Added Navbar tests for the closed/open contract, exact route boundary, Escape/focus behavior, outside-click dismissal, and EN/DE localization.


## Cross-reference occurrences outside extracted headings

- Legacy line 1295: | FE-AUTH-ENTRY-001 | Add desktop Sign in menu with User Login and Create Student Account only | AUTH-001, AUTH-002 | P0 |
- Legacy line 4243: Done:    FE-AUTH-ENTRY-001  Add desktop User Sign in menu [completed 2026-09-11]
