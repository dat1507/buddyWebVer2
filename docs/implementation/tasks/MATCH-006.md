# MATCH-006

**Control-plane status:** PLANNED / BACKLOG
**Track:** buddy-v2
**Priority:** P2
**Dependencies (latest extracted):** MATCH-003, MATCH-007

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6652-6666

### MATCH-006 — Implement Hungarian comparison algorithm

**Task ID:** `MATCH-006`
**Change:** Updated existing; **Status:** Planned; **Priority:** P2; **Phase:** 16
**Goal:** Compare assignment quality without changing candidate eligibility.
**Dependencies:** MATCH-003, MATCH-007
**Scope:** Optimization over valid pairs, explicit dummy unmatched assignments.

**Acceptance Criteria:**

- [ ] Forbidden pairs remain forbidden regardless of weight; unequal pools are supported.
- [ ] Benchmark reports compatibility/runtime against greedy.

**Out of Scope:** MVP release dependency or increasing capacity to 1:N.


## Cross-reference occurrences outside extracted headings

- Legacy line 1159:     P13 --> P16[Phase 16: Matching Research - MATCH-005 and MATCH-006]
- Legacy line 1500: | MATCH-006 | Implement Hungarian comparison algorithm | 4 | MATCH-003, MATCH-007 | P2 |
