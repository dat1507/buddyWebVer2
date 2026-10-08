# MATCH-014

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** buddy-v2
**Priority:** P0
**Dependencies (latest extracted):** MATCH-013, MATCH-007

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6351-6366

### MATCH-014 — Create guarded match publication and override APIs

**Task ID:** `MATCH-014`
**Change:** New; **Status:** Planned; **Priority:** P0; **Phase:** 13
**Goal:** Apply reviewed assignments atomically without breaking hard rules.
**Dependencies:** MATCH-013, MATCH-007
**Scope:** POST /api/admin/matching/publish and /override; idempotency, row locks, revalidation, reason/audit.

**Acceptance Criteria:**

- [ ] Publish rejects changed profile versions, expired run, same-type pair or occupied participant with 409; all-or-nothing transaction.
- [ ] Repeated publication creates no duplicates; override must pass same policy and log reason; failure rolls back match and audit.
- [ ] Pending pair responses reset on reassignment; users see only published proposals for themselves.

**Out of Scope:** Admin ability to bypass eligibility, multi-service queues or notifications backend.


## Cross-reference occurrences outside extracted headings

- Legacy line 1464: | MATCH-009 | Create own-match result endpoint | 2 | MATCH-014, AUTH-017 | P0 |
- Legacy line 1469: | MATCH-014 | Create guarded match publication and override APIs | 2 | MATCH-013, MATCH-007 | P0 |
- Legacy line 1491: | ADMIN-016 | Create matching preview and publish table | 2 | ADMIN-015, MATCH-013, MATCH-014 | P0 |
- Legacy line 1492: | ADMIN-017 | Create constrained manual match override UI | 3 | ADMIN-016, MATCH-014 | P0 |
- Legacy line 4105: | \`/api/admin/matching/publish\` | POST | ❌ | ✅ (MATCH-014; revalidate + CSRF) |
- Legacy line 4320: Superseded: MATCH-014          Admin publish/override removed by V2
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 6372: **Dependencies:** MATCH-014, AUTH-017
- Legacy line 6492: **Dependencies:** ADMIN-015, MATCH-013, MATCH-014
- Legacy line 6507: **Dependencies:** ADMIN-016, MATCH-014
