# FE-AUTH-ENTRY-003

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P1
**Dependencies (latest extracted):** AUTH-002

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2020-2031

#### FE-AUTH-ENTRY-003 — Connect Landing CTA to Registration

**Status**: Completed (✅)

- `Join the Community` becomes an internal navigation action to `/register` only after AUTH-002 exists.

**Implementation Notes**:
- Converted the CTA Section's localized `Join the Community` action from an inert button to a React Router link targeting `/register`.
- Preserved the existing primary Button visual, responsive full-width/mobile behavior, hover treatment, and visible keyboard focus style through the Button `asChild` composition.
- Kept `Watch Demo` as an independent button with its existing accessible dialog behavior; Hero actions remain outside this task's scope.
- Updated EN/DE component tests to require link semantics, the exact internal destination, keyboard focusability, and the absence of external or Admin navigation.


## Cross-reference occurrences outside extracted headings

- Legacy line 1297: | FE-AUTH-ENTRY-003 | Route Join the Community to \`/register\` | AUTH-002 | P1 |
- Legacy line 1775: - The primary action is an accessible internal link to \`/register\` (connected by FE-AUTH-ENTRY-003); the Demo action remains a keyboard-accessible \`type="button"\` that opens the local media dialog.
- Legacy line 4245: Done:    FE-AUTH-ENTRY-003  Route Join the Community to /register [completed 2026-09-11]
