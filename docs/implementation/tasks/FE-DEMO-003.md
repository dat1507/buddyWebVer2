# FE-DEMO-003

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P1
**Dependencies (latest extracted):** FE-DEMO-002

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 1937-1948

#### FE-DEMO-003 — Connect Watch Demo Trigger

**Status**: Completed (✅)

- Connect the existing `Watch Demo` CTA button to `DemoVideoDialog` without creating a new route.

**Implementation Notes**:
- `CtaSection` now owns the dialog's open state and opens it only from the existing localized `Watch Demo` / `Demo ansehen` button.
- Added `aria-haspopup`, `aria-expanded`, and `aria-controls` to expose the trigger-dialog relationship while preserving the existing responsive CTA layout.
- Kept the MP4 out of the initial DOM and network lifecycle until the User explicitly activates the trigger; no route or external navigation was added.
- Added CTA integration coverage for lazy media mounting, dialog opening, expanded state, closing, and focus return to the trigger.


## Cross-reference occurrences outside extracted headings

- Legacy line 1273: | FE-DEMO-003 | Connect Watch Demo to the video dialog | FE-DEMO-002 | P1 |
- Legacy line 1931: - Added a portal-based \`DemoVideoDialog\` controlled through \`open\` and \`onOpenChange\`, leaving trigger ownership to FE-DEMO-003.
- Legacy line 4238: Done:    FE-DEMO-003     Connect Watch Demo to the dialog [completed 2026-09-10]
