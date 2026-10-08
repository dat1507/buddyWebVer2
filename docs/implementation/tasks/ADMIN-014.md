# ADMIN-014

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-003, MATCH-013

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6457-6471

### ADMIN-014 — Create Admin Matching overview

**Task ID:** `ADMIN-014`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 15
**Goal:** Show real operational matching counts.
**Dependencies:** ADMIN-003, MATCH-013
**Scope:** Server stats for eligible, unmatched, proposed and active users/pairs.

**Acceptance Criteria:**

- [ ] Counts come from authorized stats API and are labelled accurately.
- [ ] Empty/error states do not report fabricated operational totals.

**Out of Scope:** Research dashboard.


## Cross-reference occurrences outside extracted headings

- Legacy line 1489: | ADMIN-014 | Create Admin Matching overview | 2 | ADMIN-003, MATCH-013 | P0 |
- Legacy line 1490: | ADMIN-015 | Create Run Matching control panel | 3 | ADMIN-014, MATCH-008 | P0 |
- Legacy line 1493: | ADMIN-018 | Create match history table | 2 | ADMIN-014, MATCH-013 | P1 |
- Legacy line 4204: > **Buddy Matching entries in this v2.2 order are superseded.** Preserve the completed history below, but do not execute any \`Next: MATCH-*\`, \`FE-033..037\`, or \`ADMIN-014..017\` line as written. The exact V2 order and parallel branches are in Part 26. Non-matching Event/Admin work remains independently planned.
- Legacy line 4327: Superseded: ADMIN-014          Use Part 26 ADMIN-V2-001/002 monitoring
- Legacy line 4377: User/Profile/Matching: **BE-008/009 → BE-010 → BE-011/012 → BE-014/015 → BE-016 → FE-025/026/039/027 → FE-038 → FE-023/028/029 → MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008/013/014 → MATCH-009/010 → FE-033/034/035/037 + ADMIN-014/015/016/017 → real two-user cross-type plus Admin acceptance**. The code-level Profile dependencies and local Profile/avatar persistence acceptance are complete, so MATCH-001 is ready.
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 5110: security/integration/deployment credit. ADMIN-014 still awaits MATCH-013.
- Legacy line 6477: **Dependencies:** ADMIN-014, MATCH-008
- Legacy line 6627: **Dependencies:** ADMIN-014, MATCH-013
