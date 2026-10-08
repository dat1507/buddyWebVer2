# MATCH-013

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** buddy-v2
**Priority:** P0
**Dependencies (latest extracted):** MATCH-008

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6336-6350

### MATCH-013 — Create admin matching preview and history read APIs

**Task ID:** `MATCH-013`
**Change:** New; **Status:** Planned; **Priority:** P0; **Phase:** 13
**Goal:** Supply the existing admin preview/history UI with real data.
**Dependencies:** MATCH-008
**Scope:** GET /api/admin/matching/preview?run_id=..., /history and /stats with pagination.

**Acceptance Criteria:**

- [ ] ADMIN reads run scores, explanations and unmatched reasons; USER receives 403.
- [ ] Expired/stale preview is labelled and cannot be mistaken for an active match; no candidate directory is exposed publicly.

**Out of Scope:** Finalizing or overriding pairs.


## Cross-reference occurrences outside extracted headings

- Legacy line 1468: | MATCH-013 | Create admin matching preview and history read APIs | 2 | MATCH-008 | P0 |
- Legacy line 1469: | MATCH-014 | Create guarded match publication and override APIs | 2 | MATCH-013, MATCH-007 | P0 |
- Legacy line 1489: | ADMIN-014 | Create Admin Matching overview | 2 | ADMIN-003, MATCH-013 | P0 |
- Legacy line 1491: | ADMIN-016 | Create matching preview and publish table | 2 | ADMIN-015, MATCH-013, MATCH-014 | P0 |
- Legacy line 1493: | ADMIN-018 | Create match history table | 2 | ADMIN-014, MATCH-013 | P1 |
- Legacy line 4104: | \`/api/admin/matching/preview\` | GET | ❌ | ✅ (MATCH-013) |
- Legacy line 4319: Superseded: MATCH-013          Admin preview/history contract removed by V2
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 5110: security/integration/deployment credit. ADMIN-014 still awaits MATCH-013.
- Legacy line 6356: **Dependencies:** MATCH-013, MATCH-007
- Legacy line 6462: **Dependencies:** ADMIN-003, MATCH-013
- Legacy line 6492: **Dependencies:** ADMIN-015, MATCH-013, MATCH-014
- Legacy line 6627: **Dependencies:** ADMIN-014, MATCH-013
