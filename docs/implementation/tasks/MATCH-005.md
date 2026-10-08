# MATCH-005

**Control-plane status:** PLANNED / BACKLOG
**Track:** buddy-v2
**Priority:** P2
**Dependencies (latest extracted):** MATCH-003, MATCH-007

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6637-6651

### MATCH-005 — Implement Gale-Shapley comparison algorithm

**Task ID:** `MATCH-005`
**Change:** Updated existing; **Status:** Planned; **Priority:** P2; **Phase:** 16
**Goal:** Compare stable matching after MVP establishes a baseline.
**Dependencies:** MATCH-003, MATCH-007
**Scope:** Reuse candidate matrix, deterministic rankings and hard constraints.

**Acceptance Criteria:**

- [ ] Same admissible data as greedy; constraint violation count is zero.
- [ ] Benchmark documents stability and tradeoffs on synthetic data.

**Out of Scope:** MVP release dependency or learned ranking.


## Cross-reference occurrences outside extracted headings

- Legacy line 852: MVP: deterministic greedy, 1:1 reservation, coordinator preview → explicit atomic publish → proposed → one accept remains proposed → both accept active; rejection releases the reservation. Research: MATCH-005/006 stable/optimal comparisons, followed by embeddings/hybrid and feedback learning after opt-in data/evaluation exist. No ML infrastructure is required to release basic matching.
- Legacy line 1159:     P13 --> P16[Phase 16: Matching Research - MATCH-005 and MATCH-006]
- Legacy line 1454: > **Superseded by Part 26:** Do not execute any task in this old Matching Backend table as written. No listed matching task was implemented. MATCH-002/011 feedback and MATCH-005/006/012 research may be reconsidered only after V2 with new dependencies/contracts; they are not release tasks. The V2 registry uses \`EMAIL-*\`, \`PREF-*\`, \`REC-*\`, \`INV-*\`, \`BUDDY-*\`, \`CHAT-*\`, \`ADMIN-V2-*\`, \`SEM-*\`, \`OPS-*\`, and \`ACCEPT-*\` IDs.
- Legacy line 1499: | MATCH-005 | Implement Gale-Shapley comparison algorithm | 4 | MATCH-003, MATCH-007 | P2 |
- Legacy line 4368: Deferred/recontract: MATCH-005/006            1:1 assignment research does not drive V2 recommendations
- Legacy line 4381: Core release gate: all P0 contracts, including basic matching and basic recap, pass their integration/security acceptance criteria. The landing-only milestone in the previous order is not the complete Buddy MVP. A working API plus admin-to-public checks must prove content updates without a redeploy. Calendar UI (FE-EVENT-CALENDAR-001), full recap gallery (ADMIN-EVT-002), internal registration (EVT-007/FE-032), settings password change and feedback follow as P1. MATCH-005/006 are Phase 16 research.
- Legacy line 4389: - **P2 — POST-DEMO for this deadline:** the remaining Event/EventSlider/Admin Event lane, AUTH-025/FE-024, event registration/calendar, feedback/history and MATCH-005/006 research. Their existing product-release priorities and dependencies are unchanged; this label is only the September 22 demo schedule.
