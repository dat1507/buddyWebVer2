# FE-EVENT-CALENDAR-001

**Control-plane status:** PLANNED / BACKLOG
**Track:** events
**Priority:** P1
**Dependencies (latest extracted):** FE-030, FE-031, FE-014B

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6592-6606

### FE-EVENT-CALENDAR-001 — Create Event Calendar UI after stable Event API

**Task ID:** `FE-EVENT-CALENDAR-001`
**Change:** New; **Status:** Planned; **Priority:** P1; **Phase:** 12B
**Goal:** Deliver the deferred calendar using existing event data.
**Dependencies:** FE-030, FE-031, FE-014B
**Scope:** /user/calendar with accessible month/agenda views, date navigation and category filter; then connect the landing Calendar card.

**Acceptance Criteria:**

- [ ] Uses EVT-005 date-range query; multi-day and timezone-boundary events render once correctly.
- [ ] EN/DE, mobile agenda, keyboard, empty/error states work; legacy files are visual/content reference only.

**Out of Scope:** Recurrence, Google Calendar sync, advanced filtering or a second event store.


## Cross-reference occurrences outside extracted headings

- Legacy line 1450: | FE-EVENT-CALENDAR-001 | Create Event Calendar UI after stable Event API | 2 | FE-030, FE-031, FE-014B | P1 |
- Legacy line 4364: Next: FE-EVENT-CALENDAR-001   Create Event Calendar UI after stable Event API [P1; Phase 12B]
- Legacy line 4381: Core release gate: all P0 contracts, including basic matching and basic recap, pass their integration/security acceptance criteria. The landing-only milestone in the previous order is not the complete Buddy MVP. A working API plus admin-to-public checks must prove content updates without a redeploy. Calendar UI (FE-EVENT-CALENDAR-001), full recap gallery (ADMIN-EVT-002), internal registration (EVT-007/FE-032), settings password change and feedback follow as P1. MATCH-005/006 are Phase 16 research.
- Legacy line 8518: \`FE-032\`, and \`FE-EVENT-CALENDAR-001\` remain optional/post-MVP work. \`FE-031\` no longer depends on
