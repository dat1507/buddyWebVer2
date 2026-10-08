# CHAT-001

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** BUDDY-001; Database + Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7632-7673

#### CHAT-001 — Buddy conversation and message persistence

- **Status:** **Done 2026-09-30.** Added Alembic revision `0014_buddy_chat_persistence`
  and backend-owned `BuddyConversation`/`BuddyMessage` persistence. A unique Match FK makes the
  authoritative ACTIVE `BuddyMatch` the only conversation identity; participant lists are never
  duplicated, and multiple Matches involving the same USER retain independent conversations.
- **Implementation:** `get_or_create_buddy_conversation()` uses one PostgreSQL
  `INSERT ... ON CONFLICT DO NOTHING RETURNING` operation, flushes without committing and is ready
  for INV-005 to compose into its Accept transaction. `persist_buddy_message()` accepts only a
  backend-authenticated participant, stores unchanged plain text with a nonblank/10,000-code-point
  defensive persistence bound and never commits. A PostgreSQL trigger independently derives the
  Match participants and rejects an outsider/direct write. Messages use server UTC timestamps,
  initial `expires_at=created_at+90d`, the planned first-read 30/90-day constraint foundation and
  deterministic `(created_at, id)` ordering. Conversation/message content has no edit, soft-delete,
  lifecycle status or optimistic-version field; Match→conversation→message and sender→message
  cascades support the later backed-up Semester Reset, with no normal user delete behavior.
- **Security/operations:** Both tables remain inside `app_private`, have RLS enabled and revoke
  PUBLIC/Data API access. Runtime receives read/insert only plus column-level update of
  `read_at`/`expires_at`; it cannot update sender/body or delete rows. Conversation Match lookup,
  chronological cursor reads, sender FK maintenance and expiry cleanup have exact supporting
  unique/composite indexes. The trigger is `SECURITY INVOKER`, has an empty search path and is not
  directly executable by the runtime role. No message content is logged or copied into another
  domain table.
- **Verification:** CHAT-001 model/service/offline migration tests pass (23); isolated real
  PostgreSQL acceptance passes concurrent same-Match get-or-create, reciprocal reuse, concurrent
  messages, same-timestamp deterministic ordering, multiple A-B/A-C relationships, stream
  isolation, outsider trigger rejection, runtime column grants, constraints, indexes, cascades,
  upgrade/downgrade/re-upgrade and Alembic autogenerate drift. Relevant BUDDY/profile/INV/REC
  regression passes (77 passed, 1 environment-gated skip); full backend regression passes
  (1029 passed, 27 environment-gated skips). Ruff lint, changed-file format, strict mypy (202
  source files), package sdist/wheel build, pip check, locked runtime dependency audit with zero
  known vulnerabilities, Alembic history/single head and Docker Compose validation pass. Alembic
  head is `0014_buddy_chat_persistence`. CHAT-002 retains ownership of HTTP history/send/read,
  idempotent send keys, rate limits, expired-row filtering and first-read mutation behavior.
- **Purpose:** Establish one durable 1:1 text conversation for each ACTIVE Match.
- **Scope / likely files:** BuddyConversation/BuddyMessage models/enums, exports and Alembic migration; Match relationship and retention indexes.
- **Dependencies / ownership:** BUDDY-001; Database + Backend.
- **Security:** FK sender must be a participant enforced by service/trigger strategy; body bounds/plain text; backend-only grants; indexes support authorized time-ordered reads/cleanup.
- **Acceptance / DoD:** one conversation per Match; fields include sender/body/created/read/expires; initial `expires_at=created_at+90d`; cascades/reset behavior documented without normal user delete.
- **Tests/gates:** migration/model/constraint/index/cascade tests.
- **Non-goals:** images, files, audio, voice, video, reactions or group chat.


## Cross-reference occurrences outside extracted headings

- Legacy line 6714: | Chat/realtime | **CHAT-001..005 persistence, HTTP recovery, authenticated realtime, accessible frontend and expired-message cleanup implemented** | Migrations \`0014_buddy_chat_persistence\`/\`0015_chat_send_idempotency\` provide authoritative chat storage and send idempotency; \`0016_chat_message_cleanup\` adds the bounded least-privilege cleanup function. CHAT-002 REST recovery, \`WS /api/ws/chat/{conversation_id}\`, the \`/user/buddy\` UI and the cleanup CLI cover participant-authorized history, cursor pagination, idempotent send, first-read retention, multi-worker fan-out/reconciliation and physical expiry enforcement. PostgreSQL remains authoritative. | Reuse these contracts in ADMIN/Semester work; Redis/WebSocket remain delivery-only, the frontend stores no durable message archive and the deployment scheduler invokes only the documented cleanup command. |
- Legacy line 6871: | INV-005 (**Done 2026-09-30**) | Atomic Accept | INV-003, BUDDY-001, PROFILE-V2-001, CHAT-001 | Recipient-only revalidation creates opposite-type ACTIVE Match/conversation once | Transaction/type-update-race/idempotency tests |
- Legacy line 6878: | CHAT-001 | Conversation/message persistence | BUDDY-001 | One conversation/Match; text messages and retention fields | Migration/model tests |
- Legacy line 6879: | CHAT-002 (**Done 2026-10-01**) | History/read/retention service | CHAT-001, AUTH-V2-001 | Participant-only cursor history; idempotent send; atomic first-read retention formula | API/time/auth/PostgreSQL race tests |
- Legacy line 6885: | SEM-001 (**Done 2026-10-02**) | Semester/boundary/backup metadata | BUDDY-001, CHAT-001 | Persisted cohort boundary and operation states | Migration/invariant tests |
- Legacy line 7447: - **Dependencies / ownership:** INV-003, BUDDY-001, PROFILE-V2-001, CHAT-001 when conversation creation is included; Backend + Database.
- Legacy line 7683:   derives its sender from the authenticated principal, reuses the CHAT-001 plain-text/nonblank/
- Legacy line 7706: - **Dependencies / ownership:** CHAT-001, AUTH-V2-001; Backend.
- Legacy line 7739:   safe DTO/log allowlists, rate limits and CHAT-001/002 regressions. No database migration,
- Legacy line 7861: - **Dependencies / ownership:** BUDDY-001, CHAT-001, existing User/Audit; Database + Backend.
- Legacy line 8169: BUDDY-001 → CHAT-001
- Legacy line 8174: (INV-003 + BUDDY-001 + PROFILE-V2-001 + CHAT-001) → INV-005
- Legacy line 8180: (CHAT-001 + AUTH-V2-001) → CHAT-002
- Legacy line 8186: (BUDDY-001 + CHAT-001) → SEM-001
- Legacy line 8200: Clarification of the intertwined invitation path: \`BUDDY-001\` starts after REC-002; \`PROFILE-V2-001\` and \`CHAT-001\` then branch from it and both must finish before INV-005. INV-001/002/003/004 proceed in parallel with that persistence branch. INV-005 then uses the shared profile/participant locking policy and atomically creates the opposite-type ACTIVE Match and its one conversation. \`PROFILE-V2-002\` may proceed as soon as the backend profile contract is stable.
- Legacy line 8208: 4. Complete \`BUDDY-001\`, then \`PROFILE-V2-001\`, \`PROFILE-V2-002\` and \`CHAT-001\`; \`INV-008\` may proceed once \`INV-003\` is complete.
- Legacy line 8217: - BUDDY-001→PROFILE-V2-001/CHAT-001 can run alongside INV-001→INV-004 after REC-001/002.
- Legacy line 8293: | **LOCAL** | **NOT READY (V2)** | CHAT-001..005 and ADMIN-V2-001/002 monitoring are code-complete with automated gates; authenticated two-participant browser acceptance plus Semester/reset/full vertical flows are still outstanding. |
