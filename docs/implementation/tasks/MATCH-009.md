# MATCH-009

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** buddy-v2
**Priority:** P0
**Dependencies (latest extracted):** MATCH-014, AUTH-017

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6367-6381

### MATCH-009 — Create own-match result endpoint

**Task ID:** `MATCH-009`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 13
**Goal:** Show students only their authorized published match.
**Dependencies:** MATCH-014, AUTH-017
**Scope:** GET /api/matching/my-match including safe buddy card, own response and explanation.

**Acceptance Criteria:**

- [ ] Membership check filters both participants; no foreign match ID yields another pair; no-match is a normal empty result.
- [ ] Buddy view excludes email/contact/raw availability and private preferences; private avatar access requires owner/coordinator/live-match relationship.

**Out of Scope:** Global candidate browsing or public profiles.


## Cross-reference occurrences outside extracted headings

- Legacy line 1464: | MATCH-009 | Create own-match result endpoint | 2 | MATCH-014, AUTH-017 | P0 |
- Legacy line 1465: | MATCH-010 | Create own-match accept/reject endpoint | 2 | MATCH-009, MATCH-007, AUTH-011A | P0 |
- Legacy line 1478: | FE-034 | Create match result and safe buddy card | 3 | FE-033, MATCH-009 | P0 |
- Legacy line 4321: Superseded: MATCH-009          Old own-match endpoint; use Part 26 INV/BUDDY APIs
- Legacy line 4377: User/Profile/Matching: **BE-008/009 → BE-010 → BE-011/012 → BE-014/015 → BE-016 → FE-025/026/039/027 → FE-038 → FE-023/028/029 → MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008/013/014 → MATCH-009/010 → FE-033/034/035/037 + ADMIN-014/015/016/017 → real two-user cross-type plus Admin acceptance**. The code-level Profile dependencies and local Profile/avatar persistence acceptance are complete, so MATCH-001 is ready.
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 6387: **Dependencies:** MATCH-009, MATCH-007, AUTH-011A
- Legacy line 6417: **Dependencies:** FE-033, MATCH-009
- Legacy line 6731: | Both users respond to a proposed match | No runtime support | Sender consents by sending; recipient Accept creates ACTIVE Match | Replace MATCH-009/010 and FE-035 with invitation state-machine tasks. |
