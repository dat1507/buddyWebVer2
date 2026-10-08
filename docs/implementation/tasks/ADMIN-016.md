# ADMIN-016

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-015, MATCH-013, MATCH-014

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6487-6501

### ADMIN-016 — Create matching preview and publish table

**Task ID:** `ADMIN-016`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 15
**Goal:** Review proposed assignments before making them visible.
**Dependencies:** ADMIN-015, MATCH-013, MATCH-014
**Scope:** Pair scores, constraint explanations, unmatched reasons and explicit publish action.

**Acceptance Criteria:**

- [ ] Stale preview cannot publish; conflicts request rerun rather than silently changing candidates.
- [ ] Publication updates visible states using confirmed server response.

**Out of Scope:** Editing raw matching data in browser.


## Cross-reference occurrences outside extracted headings

- Legacy line 1491: | ADMIN-016 | Create matching preview and publish table | 2 | ADMIN-015, MATCH-013, MATCH-014 | P0 |
- Legacy line 1492: | ADMIN-017 | Create constrained manual match override UI | 3 | ADMIN-016, MATCH-014 | P0 |
- Legacy line 4329: Superseded: ADMIN-016          Admin preview/publish removed by V2
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 6507: **Dependencies:** ADMIN-016, MATCH-014
