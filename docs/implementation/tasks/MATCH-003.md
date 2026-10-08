# MATCH-003

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** buddy-v2
**Priority:** P0
**Dependencies (latest extracted):** MATCH-007, BE-009

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6291-6305

### MATCH-003 — Create deterministic rule-based compatibility scoring

**Task ID:** `MATCH-003`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 13
**Goal:** Score real saved profile data after admissibility filtering.
**Dependencies:** MATCH-007, BE-009
**Scope:** Part 8 normalized interest/language/schedule/major/activity score, versioned weights and explanations.

**Acceptance Criteria:**

- [ ] Candidate input uses profile IDs and versions; scoring cannot admit an invalid pair; weights sum to one before missing-data normalization.
- [ ] Fixtures cover disjoint/shared interests and languages, absent availability, stable ties and bounded 0..100 results.

**Out of Scope:** Personality inference, embeddings, learning-to-rank and vector DB requirement.


## Cross-reference occurrences outside extracted headings

- Legacy line 1460: | MATCH-003 | Create deterministic rule-based compatibility scoring | 4 | MATCH-007, BE-009 | P0 |
- Legacy line 1461: | MATCH-004 | Implement deterministic greedy buddy assignment | 3 | MATCH-003, MATCH-007 | P0 |
- Legacy line 1467: | MATCH-012 | Create synthetic dataset generator (500 profiles) | 3 | MATCH-003 | P1 |
- Legacy line 1499: | MATCH-005 | Implement Gale-Shapley comparison algorithm | 4 | MATCH-003, MATCH-007 | P2 |
- Legacy line 1500: | MATCH-006 | Implement Hungarian comparison algorithm | 4 | MATCH-003, MATCH-007 | P2 |
- Legacy line 4316: Superseded: MATCH-003          Old weights contract; use Part 26 REC-002
- Legacy line 4377: User/Profile/Matching: **BE-008/009 → BE-010 → BE-011/012 → BE-014/015 → BE-016 → FE-025/026/039/027 → FE-038 → FE-023/028/029 → MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008/013/014 → MATCH-009/010 → FE-033/034/035/037 + ADMIN-014/015/016/017 → real two-user cross-type plus Admin acceptance**. The code-level Profile dependencies and local Profile/avatar persistence acceptance are complete, so MATCH-001 is ready.
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 6311: **Dependencies:** MATCH-003, MATCH-007
- Legacy line 6642: **Dependencies:** MATCH-003, MATCH-007
- Legacy line 6657: **Dependencies:** MATCH-003, MATCH-007
