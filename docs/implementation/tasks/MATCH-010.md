# MATCH-010

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** buddy-v2
**Priority:** P0
**Dependencies (latest extracted):** MATCH-009, MATCH-007, AUTH-011A

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6382-6396

### MATCH-010 — Create own-match accept/reject endpoint

**Task ID:** `MATCH-010`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 13
**Goal:** Make assignment confirmation explicit for both students.
**Dependencies:** MATCH-009, MATCH-007, AUTH-011A
**Scope:** POST /api/matching/respond with match/version; two participant responses and transactional status changes.

**Acceptance Criteria:**

- [ ] Only a participant can respond; retries are idempotent; first accept keeps proposal reserved, both accept activate, rejection releases both.
- [ ] Recheck hard constraints before activation; stale/withdrawn match yields 409; participants can decline even after profile becomes incomplete.

**Out of Scope:** Direct messaging, reminders or automatic reassignment after rejection.


## Cross-reference occurrences outside extracted headings

- Legacy line 1465: | MATCH-010 | Create own-match accept/reject endpoint | 2 | MATCH-009, MATCH-007, AUTH-011A | P0 |
- Legacy line 1479: | FE-035 | Create buddy match accept/reject UI | 2 | FE-034, MATCH-010 | P0 |
- Legacy line 4322: Superseded: MATCH-010          Two-party response removed; use Part 26 INV-005/006
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 6432: **Dependencies:** FE-034, MATCH-010
