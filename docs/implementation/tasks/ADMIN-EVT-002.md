# ADMIN-EVT-002

**Control-plane status:** PLANNED / BACKLOG
**Track:** events
**Priority:** P1
**Dependencies (latest extracted):** ADMIN-EVT-001, EVT-011

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6562-6576

### ADMIN-EVT-002 — Create recap gallery upload and ordering UI

**Task ID:** `ADMIN-EVT-002`
**Change:** New; **Status:** Planned; **Priority:** P1; **Phase:** 11
**Goal:** Extend recap media when the core flow is working.
**Dependencies:** ADMIN-EVT-001, EVT-011
**Scope:** Up to 20 images, localized alt text, ordering, remove/replace and cover reuse.

**Acceptance Criteria:**

- [ ] Keyboard ordering and upload errors work; removed image is cleaned only when unreferenced.
- [ ] Every attachment belongs to the same event; gallery survives reload.

**Out of Scope:** Video processing or external media providers.


## Cross-reference occurrences outside extracted headings

- Legacy line 1421: | ADMIN-EVT-002 | Create recap gallery upload and ordering UI | 2 | ADMIN-EVT-001, EVT-011 | P1 |
- Legacy line 4361: Next: ADMIN-EVT-002           Create recap gallery upload and ordering UI [P1; Phase 11]
- Legacy line 4381: Core release gate: all P0 contracts, including basic matching and basic recap, pass their integration/security acceptance criteria. The landing-only milestone in the previous order is not the complete Buddy MVP. A working API plus admin-to-public checks must prove content updates without a redeploy. Calendar UI (FE-EVENT-CALENDAR-001), full recap gallery (ADMIN-EVT-002), internal registration (EVT-007/FE-032), settings password change and feedback follow as P1. MATCH-005/006 are Phase 16 research.
