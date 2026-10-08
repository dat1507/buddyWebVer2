# ADMIN-010

**Control-plane status:** PLANNED / BACKLOG
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-005, ADMIN-006, EVT-009

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6197-6211

### ADMIN-010 — Create event deletion with dependency-aware confirmation

**Task ID:** `ADMIN-010`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 11
**Goal:** Delete eligible content without leaving broken relationships.
**Dependencies:** ADMIN-005, ADMIN-006, EVT-009
**Scope:** Confirm dialog and API dependency/conflict feedback.

**Acceptance Criteria:**

- [ ] Blocking registrations/published recap are explained; 409 leaves UI record intact.
- [ ] Successful deletion refreshes lists and linked sliders; users never type filesystem paths.

**Out of Scope:** Bulk destructive deletion.


## Cross-reference occurrences outside extracted headings

- Legacy line 1416: | ADMIN-010 | Create event deletion with dependency-aware confirmation | 2 | ADMIN-005, ADMIN-006, EVT-009 | P0 |
- Legacy line 1444: | FE-014B | Verify live Event Slider integration and linked Event freshness | 2 | FE-014, EVS-007, ADMIN-SLIDER-004, ADMIN-010, FE-031 | P0 |
- Legacy line 4347: Next: ADMIN-010               Create event deletion with dependency-aware confirmation [P0; Phase 11]
- Legacy line 5192: This keeps ADMIN-010 and ADMIN-SLIDER-003 domain policy outside the primitive while allowing them to
- Legacy line 6247: **Dependencies:** FE-014, EVS-007, ADMIN-SLIDER-004, ADMIN-010, FE-031
- Legacy line 8448:   retryable and must not resurrect the Event. \`ADMIN-010\` UI remains optional follow-up even though
- Legacy line 8517: \`EVT-007\`, \`EVT-012\`, \`EVT-013\`, \`ADMIN-010\`, \`ADMIN-011\`, \`ADMIN-EVT-001/002\`, \`FE-030\`,
- Legacy line 8986: - **Delete Event UI:** backend service/delete contract is preserved; \`ADMIN-010\` remains optional
