# ADMIN-011

**Control-plane status:** PLANNED / BACKLOG
**Track:** admin
**Priority:** P1
**Dependencies (latest extracted):** ADMIN-006, EVT-007

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6547-6561

### ADMIN-011 — Create admin event registration detail view

**Task ID:** `ADMIN-011`
**Change:** Updated existing; **Status:** Planned; **Priority:** P1; **Phase:** 11
**Goal:** Use registration data only after internal RSVP is delivered.
**Dependencies:** ADMIN-006, EVT-007
**Scope:** Admin registration list from /api/admin/events/:id/registrations.

**Acceptance Criteria:**

- [ ] Only ADMIN sees bounded attendee fields; lists support empty/pagination states.
- [ ] External-link-only event shows no internal registrations rather than fabricated counts.

**Out of Scope:** Publishing attendee names in recaps.


## Cross-reference occurrences outside extracted headings

- Legacy line 1417: | ADMIN-011 | Create admin event registration detail view | 2 | ADMIN-006, EVT-007 | P1 |
- Legacy line 4076: | \`/api/admin/events/:id/registrations\` | GET | ADMIN, later internal registration | EVT-007 / ADMIN-011 |
- Legacy line 4360: Next: ADMIN-011               Create admin event registration detail view [P1; Phase 11]
- Legacy line 5918: or admin registration views (EVT-007/ADMIN-011).
- Legacy line 8517: \`EVT-007\`, \`EVT-012\`, \`EVT-013\`, \`ADMIN-010\`, \`ADMIN-011\`, \`ADMIN-EVT-001/002\`, \`FE-030\`,
