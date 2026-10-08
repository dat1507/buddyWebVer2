# MATCH-004

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** buddy-v2
**Priority:** P0
**Dependencies (latest extracted):** MATCH-003, MATCH-007

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6306-6320

### MATCH-004 — Implement deterministic greedy buddy assignment

**Task ID:** `MATCH-004`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 13
**Goal:** Produce understandable MVP recommendations for 100–150 users.
**Dependencies:** MATCH-003, MATCH-007
**Scope:** Sort allowed pairs by score then stable profile IDs; select non-conflicting pairs and unmatched reasons.

**Acceptance Criteria:**

- [ ] Same input yields same pair set; each profile used at most once; empty/unequal groups never force invalid pairs.
- [ ] Tests cover same-type exclusion and reservation conflicts; run remains bounded for 150 profiles.

**Out of Scope:** Optimization solvers or second algorithm required for MVP.


## Cross-reference occurrences outside extracted headings

- Legacy line 1461: | MATCH-004 | Implement deterministic greedy buddy assignment | 3 | MATCH-003, MATCH-007 | P0 |
- Legacy line 1463: | MATCH-008 | Create admin matching run and preview persistence | 3 | MATCH-004, AUTH-018, EVT-008 | P0 |
- Legacy line 4317: Superseded: MATCH-004          Greedy assignment removed by V2
- Legacy line 4377: User/Profile/Matching: **BE-008/009 → BE-010 → BE-011/012 → BE-014/015 → BE-016 → FE-025/026/039/027 → FE-038 → FE-023/028/029 → MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008/013/014 → MATCH-009/010 → FE-033/034/035/037 + ADMIN-014/015/016/017 → real two-user cross-type plus Admin acceptance**. The code-level Profile dependencies and local Profile/avatar persistence acceptance are complete, so MATCH-001 is ready.
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 6326: **Dependencies:** MATCH-004, AUTH-018, EVT-008
- Legacy line 6728: | Deterministic greedy 1:1 assignment | Not implemented | Recommendation only; no assignment | Withdraw MATCH-004; use \`REC-*\`. |
