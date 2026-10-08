# BUDDY-001

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** REC-002; Database + Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7201-7237

#### BUDDY-001 — ACTIVE Match persistence and unordered-pair uniqueness

- **Status:** **Done 2026-09-30.** Added Alembic revision `0013_active_match_persistence`
  and the backend-owned `BuddyMatch`/ACTIVE-only model. PostgreSQL derives the canonical unordered
  participant pair with stored `LEAST`/`GREATEST` columns and enforces at most one ACTIVE row per
  pair with a partial unique index; no per-user unique constraint exists, so one user can retain
  multiple Buddies. Each Match has one unique accepted-invitation provenance record, participant
  user/profile FKs, a bounded score plus public numeric compatibility snapshot, activation/audit
  timestamps and the planned nullable `semester_id`. `SEM-001` retains ownership of the
  authoritative semester table, backfill and FK instead of BUDDY-001 inventing a competing
  lifecycle.
- **Implementation:** The activation foundation accepts only an already-ACCEPTED invitation,
  locks both current USER/profile participants in deterministic UUID order, revalidates the
  invitation under lock, requires exactly one VIETNAMESE and one INTERNATIONAL profile, checks the
  ACTIVE canonical pair and relies on the database unique guard for the final race. It flushes but
  never commits so INV-005 can compose it into one atomic Accept transaction. Participant columns
  are immutable through least-privilege runtime grants: backend runtime receives SELECT/INSERT
  only, RLS is enabled, and public/Data API roles are revoked. INV-003's temporary accepted-history
  marker now queries the authoritative ACTIVE Match; accepted invitation history without a Match
  does not independently block a new send. REC eligibility remains unchanged.
- **Verification:** BUDDY/INV targeted model/service/offline-migration/Alembic regressions pass
  (**50 tests**). Isolated PostgreSQL acceptance passes same-direction and reciprocal concurrent
  activation with exactly one winner, stable loser conflict, multi-Buddy persistence, same-type
  rejection, DB uniqueness/constraints, participant indexes, grants/RLS, upgrade/downgrade/
  re-upgrade and autogenerate drift. Updated INV-003 PostgreSQL acceptance also passes. Full backend
  passes **1002 tests / 25 configured live skips**; Ruff, strict mypy (**193 source files**), pip
  consistency, sdist/wheel build, locked runtime dependency audit (zero known vulnerabilities),
  Alembic history/single head and Docker Compose validation pass. Previous head
  `0012_invitation_persistence`; final head `0013_active_match_persistence`.
- **Purpose:** Persist accepted Buddy relationships while allowing multiple Buddies per user.
- **Scope / likely files:** new Match model/status/schema, exports and Alembic migration; canonical unordered user pair and invitation provenance.
- **Dependencies / ownership:** REC-002; Database + Backend.
- **Security:** FKs to current users/profiles, backend-only grants, immutable participants after activation, score snapshot excludes sensitive data; service activation requires one VIETNAMESE and one INTERNATIONAL profile.
- **Acceptance / DoD:** only ACTIVE is needed for MVP; no per-user reservation/unique constraint; database prevents a second ACTIVE row for the same unordered pair; both participant directions query efficiently; accepted types are revalidated at activation and no process rewrites existing Match participants/types.
- **Tests/gates:** migration upgrade/downgrade, pair-order uniqueness, opposite/same-type activation, concurrent insert and multi-Buddy tests.
- **Non-goals:** PROPOSED, ADMIN_APPROVED, user Unmatch/End Buddy or Admin activation.


## Cross-reference occurrences outside extracted headings

- Legacy line 4314: Superseded: MATCH-001          Old Match/reservation persistence contract; use Part 26 BUDDY-001
- Legacy line 6864: | BUDDY-001 (**Done 2026-09-30**) | ACTIVE Match persistence | REC-002 | Opposite-type activation; multiple Buddies; unique ACTIVE unordered pair | Migration/type/race tests |
- Legacy line 6865: | PROFILE-V2-001 (**Done 2026-09-30**) | Lock \`student_type\` after ACTIVE Match | BUDDY-001, BE-012 | Backend rejects type change; Accept/update race preserves opposite types | API/policy/concurrency tests |
- Legacy line 6871: | INV-005 (**Done 2026-09-30**) | Atomic Accept | INV-003, BUDDY-001, PROFILE-V2-001, CHAT-001 | Recipient-only revalidation creates opposite-type ACTIVE Match/conversation once | Transaction/type-update-race/idempotency tests |
- Legacy line 6876: | BUDDY-002 (**Done 2026-10-01**) | Current Buddies API | BUDDY-001, INV-005 | All ACTIVE buddies with safe snapshots | Auth/privacy/query tests |
- Legacy line 6878: | CHAT-001 | Conversation/message persistence | BUDDY-001 | One conversation/Match; text messages and retention fields | Migration/model tests |
- Legacy line 6885: | SEM-001 (**Done 2026-10-02**) | Semester/boundary/backup metadata | BUDDY-001, CHAT-001 | Persisted cohort boundary and operation states | Migration/invariant tests |
- Legacy line 7152:   reservation or per-user ACTIVE-Buddy exclusion. BUDDY-001 remains the owner of the future ACTIVE
- Legacy line 7255:   waiter blocks without deadlock, and leaves zero same-type ACTIVE Matches; the BUDDY-001 live race
- Legacy line 7263: - **Dependencies / ownership:** BUDDY-001, BE-012; Backend + Database.
- Legacy line 7447: - **Dependencies / ownership:** INV-003, BUDDY-001, PROFILE-V2-001, CHAT-001 when conversation creation is included; Backend + Database.
- Legacy line 7576: - **Dependencies / ownership:** BUDDY-001, INV-005, AUTH-V2-001; Backend.
- Legacy line 7668: - **Dependencies / ownership:** BUDDY-001; Database + Backend.
- Legacy line 7861: - **Dependencies / ownership:** BUDDY-001, CHAT-001, existing User/Audit; Database + Backend.
- Legacy line 8167: REC-002 → BUDDY-001
- Legacy line 8168: BUDDY-001 → PROFILE-V2-001 → PROFILE-V2-002
- Legacy line 8169: BUDDY-001 → CHAT-001
- Legacy line 8174: (INV-003 + BUDDY-001 + PROFILE-V2-001 + CHAT-001) → INV-005
- Legacy line 8186: (BUDDY-001 + CHAT-001) → SEM-001
- Legacy line 8200: Clarification of the intertwined invitation path: \`BUDDY-001\` starts after REC-002; \`PROFILE-V2-001\` and \`CHAT-001\` then branch from it and both must finish before INV-005. INV-001/002/003/004 proceed in parallel with that persistence branch. INV-005 then uses the shared profile/participant locking policy and atomically creates the opposite-type ACTIVE Match and its one conversation. \`PROFILE-V2-002\` may proceed as soon as the backend profile contract is stable.
- Legacy line 8208: 4. Complete \`BUDDY-001\`, then \`PROFILE-V2-001\`, \`PROFILE-V2-002\` and \`CHAT-001\`; \`INV-008\` may proceed once \`INV-003\` is complete.
- Legacy line 8217: - BUDDY-001→PROFILE-V2-001/CHAT-001 can run alongside INV-001→INV-004 after REC-001/002.
