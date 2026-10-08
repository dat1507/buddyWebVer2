# MATCH-001

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** buddy-v2
**Priority:** P0
**Dependencies (latest extracted):** BE-010

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6258-6274

### MATCH-001 — Create Match model and persistence constraints

> **SUPERSEDED — DO NOT IMPLEMENT:** This historical matching block assumes global 1:1 reservation and/or Admin-run/publish/override. No task in the block was implemented. Use the V2 contracts in Part 26; feedback/research tasks require later V2 re-contracting, and completed historical tasks elsewhere remain untouched.

**Task ID:** `MATCH-001`
**Change:** Updated existing; **Status:** Planned — READY; **Priority:** P0; **Phase:** 13
**Goal:** Record accountable pairs without duplicate active allocations.
**Dependencies:** BE-010
**Scope:** Match and MatchingRun models/migrations (run table before run_id FK); international student_id and Vietnamese buddy_id reference profiles; score metadata, statuses and user responses.

**Acceptance Criteria:**

- [ ] No self-pair, duplicate live participant or pair; proposed/accepted/active reserve both users in MVP 1:1.
- [ ] Database trigger validates opposite stored student types and serializes participant reservations; service locking also rechecks eligibility.

**Out of Scope:** Multiple concurrent program cohorts or 1:N capacity scheduling.


## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1458: | MATCH-001 | Create Match model and persistence constraints | 2 | BE-010 | P0 |
- Legacy line 1459: | MATCH-002 | Create MatchFeedback model + migration | 1 | MATCH-001 | P1 |
- Legacy line 1462: | MATCH-007 | Implement shared eligibility and candidate hard-constraint policy | 3 | MATCH-001, BE-016 | P0 |
- Legacy line 4314: Superseded: MATCH-001          Old Match/reservation persistence contract; use Part 26 BUDDY-001
- Legacy line 4377: User/Profile/Matching: **BE-008/009 → BE-010 → BE-011/012 → BE-014/015 → BE-016 → FE-025/026/039/027 → FE-038 → FE-023/028/029 → MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008/013/014 → MATCH-009/010 → FE-033/034/035/037 + ADMIN-014/015/016/017 → real two-user cross-type plus Admin acceptance**. The code-level Profile dependencies and local Profile/avatar persistence acceptance are complete, so MATCH-001 is ready.
- Legacy line 4387: - **P0 — MUST HAVE FOR DEMO:** MATCH-001, MATCH-007, MATCH-003, MATCH-004, MATCH-008, MATCH-013, MATCH-014, MATCH-009, MATCH-010, FE-033, FE-034, FE-035, FE-037, ADMIN-014, ADMIN-015 and ADMIN-016; then a real two-student plus Admin local acceptance run against migrated PostgreSQL and configured private image storage.
- Legacy line 4393: \`MATCH-001 → MATCH-007 → MATCH-003 → MATCH-004 → MATCH-008 → MATCH-013 → MATCH-014 → MATCH-009 → MATCH-010 → FE-033 → FE-034 → FE-035 → FE-037 → ADMIN-014 → ADMIN-015 → ADMIN-016 → real local two-user cross-type plus Admin acceptance\`
- Legacy line 4395: The prerequisite Profile path is no longer a MATCH-001 blocker: the configured local environment, migrated PostgreSQL database, backend-owned session flow and real avatar upload/crop/reload persistence have passed, while automated coverage verifies both Vietnamese and international Profile rules. The final runtime gate belongs at the end of the vertical slice and must verify the complete two-user cross-type matching workflow.
- Legacy line 4399: **Next development task: MATCH-001 — Create Match model and persistence constraints. Dependency BE-010 is DONE and the local Profile/runtime prerequisite has passed, so MATCH-001 is READY. AUTH-020 production acceptance remains pending operator-provided Redis/TLS/ingress configuration and is a deployment gate, not a blocker for local Matching development. Continue the direct-to-main workflow; execute MATCH-001 only when explicitly requested.**
- Legacy line 5562: **Scope:** GET /api/profile/completion; derived readiness, percentage and reason codes under Part 7 rules. Before MATCH-001 ships, reservation count is zero; MATCH-007 integrates the real reservation reader and removes this staged assumption before matching release.
- Legacy line 6280: **Dependencies:** MATCH-001, BE-016
