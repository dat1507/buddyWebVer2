# MATCH-007

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** buddy-v2
**Priority:** P0
**Dependencies (latest extracted):** MATCH-001, BE-016

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6275-6290

### MATCH-007 — Implement shared eligibility and candidate hard-constraint policy

**Task ID:** `MATCH-007`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 13
**Goal:** Filter impossible candidates before any scoring or algorithm.
**Dependencies:** MATCH-001, BE-016
**Scope:** Build opposite-group candidate pairs from complete active opted-in profiles; exclude reserved users; policy reused at run/publish/respond/override.

**Acceptance Criteria:**

- [ ] VIETNAMESE↔VIETNAMESE and INTERNATIONAL↔INTERNATIONAL are always rejected, including admin override.
- [ ] Both profiles require valid name/type/avatar/interest/language, and no self/disabled/opted-out/reserved candidates; empty or unequal pools leave explicit unmatched reasons.
- [ ] Concurrent type changes or match allocation cannot bypass commit-time checks.

**Out of Scope:** Algorithm ranking, nationality inference or gender constraint.


## Cross-reference occurrences outside extracted headings

- Legacy line 840: First load canonical eligible profiles and form only VIETNAMESE × INTERNATIONAL candidate pairs (MATCH-007). Score normalized catalog IDs and structured preferences, never auth fields or a separate mock profile store.
- Legacy line 1460: | MATCH-003 | Create deterministic rule-based compatibility scoring | 4 | MATCH-007, BE-009 | P0 |
- Legacy line 1461: | MATCH-004 | Implement deterministic greedy buddy assignment | 3 | MATCH-003, MATCH-007 | P0 |
- Legacy line 1462: | MATCH-007 | Implement shared eligibility and candidate hard-constraint policy | 3 | MATCH-001, BE-016 | P0 |
- Legacy line 1465: | MATCH-010 | Create own-match accept/reject endpoint | 2 | MATCH-009, MATCH-007, AUTH-011A | P0 |
- Legacy line 1469: | MATCH-014 | Create guarded match publication and override APIs | 2 | MATCH-013, MATCH-007 | P0 |
- Legacy line 1499: | MATCH-005 | Implement Gale-Shapley comparison algorithm | 4 | MATCH-003, MATCH-007 | P2 |
- Legacy line 1500: | MATCH-006 | Implement Hungarian comparison algorithm | 4 | MATCH-003, MATCH-007 | P2 |
- Legacy line 4315: Superseded: MATCH-007          Old reservation eligibility contract; use Part 26 REC-001
- Legacy line 4377: User/Profile/Matching: **BE-008/009 → BE-010 → BE-011/012 → BE-014/015 → BE-016 → FE-025/026/039/027 → FE-038 → FE-023/028/029 → MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008/013/014 → MATCH-009/010 → FE-033/034/035/037 + ADMIN-014/015/016/017 → real two-user cross-type plus Admin acceptance**. The code-level Profile dependencies and local Profile/avatar persistence acceptance are complete, so MATCH-001 is ready.
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 5562: **Scope:** GET /api/profile/completion; derived readiness, percentage and reason codes under Part 7 rules. Before MATCH-001 ships, reservation count is zero; MATCH-007 integrates the real reservation reader and removes this staged assumption before matching release.
- Legacy line 5576: documented pre-MATCH-001 result is zero for later replacement by MATCH-007.
- Legacy line 6296: **Dependencies:** MATCH-007, BE-009
- Legacy line 6311: **Dependencies:** MATCH-003, MATCH-007
- Legacy line 6356: **Dependencies:** MATCH-013, MATCH-007
- Legacy line 6387: **Dependencies:** MATCH-009, MATCH-007, AUTH-011A
- Legacy line 6642: **Dependencies:** MATCH-003, MATCH-007
- Legacy line 6657: **Dependencies:** MATCH-003, MATCH-007
