# ADMIN-017

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-016, MATCH-014

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6502-6516

### ADMIN-017 — Create constrained manual match override UI

**Task ID:** `ADMIN-017`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 15
**Goal:** Support coordinator correction under the same program rules.
**Dependencies:** ADMIN-016, MATCH-014
**Scope:** Reassignment selection, required reason and backend validation feedback.

**Acceptance Criteria:**

- [ ] Same-type/ineligible candidate is rejected even if UI request is modified; reason appears in audit.
- [ ] Concurrent change returns 409 and offers reload.

**Out of Scope:** Bypassing hard constraints or bulk manual SQL.


## Cross-reference occurrences outside extracted headings

- Legacy line 1492: | ADMIN-017 | Create constrained manual match override UI | 3 | ADMIN-016, MATCH-014 | P0 |
- Legacy line 4330: Superseded: ADMIN-017          Admin manual override removed by V2
- Legacy line 4388: - **P1 — SHOULD HAVE:** ADMIN-017 constrained manual override and clear seeded/demo operator notes. These improve recovery during the demo but do not replace the algorithmic run/publish path.
