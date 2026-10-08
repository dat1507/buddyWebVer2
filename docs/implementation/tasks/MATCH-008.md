# MATCH-008

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** buddy-v2
**Priority:** P0
**Dependencies (latest extracted):** MATCH-004, AUTH-018, EVT-008

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6321-6335

### MATCH-008 — Create admin matching run and preview persistence

**Task ID:** `MATCH-008`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 13
**Goal:** Generate a reviewable proposal before user-visible publication.
**Dependencies:** MATCH-004, AUTH-018, EVT-008
**Scope:** POST /api/admin/matching/run; persisted MatchingRun with algorithm/weights/profile versions and expiry.

**Acceptance Criteria:**

- [ ] Run computes proposals from DB profiles and returns a run ID; no user-visible match is created until publish.
- [ ] MVP only accepts greedy; ADMIN+CSRF enforced; audit contains no unnecessary personal data.

**Out of Scope:** Publishing automatically or executing research algorithms before delivery.


## Cross-reference occurrences outside extracted headings

- Legacy line 1463: | MATCH-008 | Create admin matching run and preview persistence | 3 | MATCH-004, AUTH-018, EVT-008 | P0 |
- Legacy line 1468: | MATCH-013 | Create admin matching preview and history read APIs | 2 | MATCH-008 | P0 |
- Legacy line 1490: | ADMIN-015 | Create Run Matching control panel | 3 | ADMIN-014, MATCH-008 | P0 |
- Legacy line 4318: Superseded: MATCH-008          Admin matching run removed by V2
- Legacy line 4377: User/Profile/Matching: **BE-008/009 → BE-010 → BE-011/012 → BE-014/015 → BE-016 → FE-025/026/039/027 → FE-038 → FE-023/028/029 → MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008/013/014 → MATCH-009/010 → FE-033/034/035/037 + ADMIN-014/015/016/017 → real two-user cross-type plus Admin acceptance**. The code-level Profile dependencies and local Profile/avatar persistence acceptance are complete, so MATCH-001 is ready.
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 6341: **Dependencies:** MATCH-008
- Legacy line 6477: **Dependencies:** ADMIN-014, MATCH-008
- Legacy line 6730: | Admin run → preview → publish → override | Admin page is placeholder | Admin monitoring only | Withdraw MATCH-008/013/014 and ADMIN-015/016/017. |
