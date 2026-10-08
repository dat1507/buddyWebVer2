# PROFILE-V2-001

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** BUDDY-001, BE-012; Backend + Database.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7238-7268

#### PROFILE-V2-001 — Backend `student_type` lock after ACTIVE Match

- **Status:** **Done 2026-09-30.** Own-profile updates now treat the persisted ACTIVE Match as the
  authoritative lock. An actual `student_type` change with at least one ACTIVE Match returns the
  stable sanitized HTTP 409 reason `STUDENT_TYPE_LOCKED_ACTIVE_MATCH`; same-value resubmission keeps
  the existing successful update/version semantics, and unrelated profile fields remain editable.
  No Match, participant type, invitation or relationship lifecycle state is rewritten.
- **Implementation:** A shared Buddy participant policy now locks current USER rows in deterministic
  UUID order and exposes a bounded indexed ACTIVE-Match `EXISTS` query without loading Match
  snapshots. Match activation and type-changing profile updates both acquire USER locks before
  profile locks, keep the transaction short and revalidate their invariant after waiting. Profile
  updates preserve stale-version precedence, perform the Match check before any requested field or
  preference mutation, and rely on the existing router CSRF/owner authentication boundary. This
  gives either concurrent operation permission to win first while forcing the waiter to observe and
  reject any state that would otherwise create a same-type ACTIVE Match.
- **Verification:** **47 targeted service/API/policy/live tests** and **199 profile/PREF/REC/INV/BUDDY
  regression tests** pass. Isolated PostgreSQL acceptance passes both lock winner orders, proves the
  waiter blocks without deadlock, and leaves zero same-type ACTIVE Matches; the BUDDY-001 live race
  regression also passes after the shared lock refactor. Full backend passes **1013 tests / 26
  configured live skips**. Ruff, strict mypy (**195 source files**), pip consistency, sdist/wheel
  build, locked dependency audit (zero known vulnerabilities), Alembic history/single head,
  autogenerate drift in the live acceptance database and Docker Compose validation pass. No
  migration is required; Alembic head remains `0013_active_match_persistence`.
- **Purpose:** Preserve the opposite-type invariant of every current Buddy relationship.
- **Scope / likely files:** existing own-profile update schema/service/router plus a shared ACTIVE-Match policy/query and stable conflict mapping; coordinate participant locks with INV-005 Accept.
- **Dependencies / ownership:** BUDDY-001, BE-012; Backend + Database.
- **Security:** backend is authoritative. A request that changes the normalized persisted type must lock/recheck the USER's ACTIVE Matches in the same transaction; use the same stable participant lock order as Accept. Never trust a disabled frontend field.
- **Acceptance / DoD:** with zero ACTIVE Matches, a valid type change still works; with one or many ACTIVE Matches, a changed type is rejected as `STUDENT_TYPE_LOCKED_ACTIVE_MATCH`; unchanged resubmission is allowed; existing Matches are unchanged; no Unmatch/End workaround is introduced. Reset deletes old USER accounts, so a new-cohort registration selects type from scratch.
- **Tests/gates:** backend API/service tests cover zero/one/many ACTIVE Matches, both current types, unchanged resubmission, stale clients and authorization; deterministic Accept-vs-profile-update concurrency tests prove neither interleaving can commit a same-type ACTIVE Match.
- **Non-goals:** automatically migrating Matches, editing the other participant, Unmatch/End Buddy, or carrying the old account into the next semester.


## Cross-reference occurrences outside extracted headings

- Legacy line 6733: | Profile type remains freely editable | Existing own-profile update can change \`student_type\`; no Match table exists yet | Backend rejects a type change whenever either participant has at least one ACTIVE Match | Add \`PROFILE-V2-001/002\`; serialize the update against Accept and expose a stable lock reason. Do not mutate existing Matches or add Unmatch. |
- Legacy line 6865: | PROFILE-V2-001 (**Done 2026-09-30**) | Lock \`student_type\` after ACTIVE Match | BUDDY-001, BE-012 | Backend rejects type change; Accept/update race preserves opposite types | API/policy/concurrency tests |
- Legacy line 6866: | PROFILE-V2-002 (**Done 2026-09-30**) | Locked \`student_type\` profile UX | PROFILE-V2-001, FE-029 | Disabled field, explanation and stale-conflict handling | Component/a11y/integration tests |
- Legacy line 6871: | INV-005 (**Done 2026-09-30**) | Atomic Accept | INV-003, BUDDY-001, PROFILE-V2-001, CHAT-001 | Recipient-only revalidation creates opposite-type ACTIVE Match/conversation once | Transaction/type-update-race/idempotency tests |
- Legacy line 7297: - **Dependencies / ownership:** PROFILE-V2-001, FE-029; Frontend.
- Legacy line 7447: - **Dependencies / ownership:** INV-003, BUDDY-001, PROFILE-V2-001, CHAT-001 when conversation creation is included; Backend + Database.
- Legacy line 8168: BUDDY-001 → PROFILE-V2-001 → PROFILE-V2-002
- Legacy line 8174: (INV-003 + BUDDY-001 + PROFILE-V2-001 + CHAT-001) → INV-005
- Legacy line 8200: Clarification of the intertwined invitation path: \`BUDDY-001\` starts after REC-002; \`PROFILE-V2-001\` and \`CHAT-001\` then branch from it and both must finish before INV-005. INV-001/002/003/004 proceed in parallel with that persistence branch. INV-005 then uses the shared profile/participant locking policy and atomically creates the opposite-type ACTIVE Match and its one conversation. \`PROFILE-V2-002\` may proceed as soon as the backend profile contract is stable.
- Legacy line 8208: 4. Complete \`BUDDY-001\`, then \`PROFILE-V2-001\`, \`PROFILE-V2-002\` and \`CHAT-001\`; \`INV-008\` may proceed once \`INV-003\` is complete.
- Legacy line 8217: - BUDDY-001→PROFILE-V2-001/CHAT-001 can run alongside INV-001→INV-004 after REC-001/002.
- Legacy line 8310: 1. **\`student_type\` after ACTIVE Match.** Backend rejects a changed \`student_type\` whenever the USER has at least one ACTIVE Match. Frontend locks the field and explains why, but backend is the authority. Existing Matches are not changed or migrated, and no Unmatch/End Buddy feature is added. The type is therefore fixed for the remainder of that account's semester after its first ACTIVE Match. Semester Reset deletes old USER accounts; a new cohort registers and selects type normally. This requirement is implemented by \`PROFILE-V2-001/002\` and is a dependency of \`INV-005\`.
