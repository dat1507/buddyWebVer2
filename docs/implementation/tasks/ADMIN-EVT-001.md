# ADMIN-EVT-001

**Control-plane status:** PLANNED / BACKLOG
**Track:** events
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-008, EVT-013

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6212-6226

### ADMIN-EVT-001 — Create recap editor and publish controls

**Task ID:** `ADMIN-EVT-001`
**Change:** New; **Status:** Planned; **Priority:** P0; **Phase:** 11
**Goal:** Allow coordinators to publish summaries of completed events.
**Dependencies:** ADMIN-008, EVT-013
**Scope:** Recap tab under /admin/events/:id; localized title/summary/body, cover and publication.

**Acceptance Criteria:**

- [ ] Draft recap survives reload; publishing invalid or future-event recap reports server validation.
- [ ] Published recap opens on canonical detail route and appears without frontend redeployment.

**Out of Scope:** Rich text HTML editor and gallery ordering.


## Cross-reference occurrences outside extracted headings

- Legacy line 1420: | ADMIN-EVT-001 | Create recap editor and publish controls | 2 | ADMIN-008, EVT-013 | P0 |
- Legacy line 1421: | ADMIN-EVT-002 | Create recap gallery upload and ordering UI | 2 | ADMIN-EVT-001, EVT-011 | P1 |
- Legacy line 4350: Next: ADMIN-EVT-001           Create recap editor and publish controls [P0; Phase 11]
- Legacy line 4379: Event/Admin: **EVT-001/002/010 → EVT-003 → EVT-004/005/006 → EVT-009/011 → EVT-012/013 → ADMIN-006..010 + ADMIN-EVT-001 → EVS-001/002/004/005/006/007 → ADMIN-SLIDER-001..004 → FE-031 → FE-014B**. Existing EVS-003 has already supplied shared storage. The two tracks may proceed independently after shared auth/storage/audit; for the demo deadline, pause the Event lane after completed EVT-004 and resume it after the Matching demo slice. This is sequencing guidance, not an instruction to spawn agents.
- Legacy line 6567: **Dependencies:** ADMIN-EVT-001, EVT-011
- Legacy line 8517: \`EVT-007\`, \`EVT-012\`, \`EVT-013\`, \`ADMIN-010\`, \`ADMIN-011\`, \`ADMIN-EVT-001/002\`, \`FE-030\`,
