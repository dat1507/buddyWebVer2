# BUDDY-002

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** BUDDY-001, INV-005, AUTH-V2-001; Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7568-7597

#### BUDDY-002 — Current Buddies API

- **Status:** **Done 2026-10-01.** `GET /api/matching/buddies` now returns one private,
  owner-filtered page of authoritative ACTIVE `BuddyMatch` relationships for the current VERIFIED
  USER. It supports multiple Buddies and never derives relationship state from invitations,
  recommendations or browser state.
- **Purpose:** Return all ACTIVE relationships for the verified participant.
- **Scope / likely files:** matching router/query/schema, safe profile/availability/shared-signal projections and conversation link/ID.
- **Dependencies / ownership:** BUDDY-001, INV-005, AUTH-V2-001; Backend.
- **Security:** participant filter at query, no email/auth/internal fields, private no-store response, signed avatar authorization extended to active participants.
- **Acceptance / DoD:** zero/one/many ACTIVE matches return deterministically; same Buddy cannot duplicate; email change locks but never deletes; each item points only to its correct conversation.
- **Tests/gates:** multi-Buddy, IDOR/privacy, locked/unlocked and query-count tests.
- **Implementation / verification:** the endpoint reuses the shared VERIFIED capability guard and
  privacy-safe batched participant profile/preferences projection. Query ownership is fixed from the
  authenticated principal, filters only live ACTIVE Matches, joins the one exact Match conversation,
  and orders by `activated_at DESC, match_id DESC`; bounded `page`/`page_size` pagination defaults to
  20 and caps at 50. Each item exposes only opaque Match/conversation IDs, the safe Buddy profile,
  and the validated persisted public numeric compatibility score/explanation/reference week—never a
  recomputed recommendation, User ID, email, invitation message, normalized key, storage metadata,
  auth/session data or raw Match internals. Non-empty reads use two relationship queries plus the
  existing five fixed profile batch queries, independent of item count. Signed avatar delivery now
  also authorizes the exact opposite profile side of an ACTIVE Match while retaining independent
  VERIFIED and resource checks. Focused tests pass **44 cases**, relevant BUDDY/profile/INV/CHAT
  regressions pass **138 cases**, and the full backend suite passes **1,139 tests with 29 configured
  live skips**. Ruff, strict mypy (**216 source files**), changed-file formatting, package build,
  `pip check`, zero-vulnerability dependency audit, Alembic history/single head and Docker Compose
  validation pass. No frontend, schema, migration or dependency change was required; Alembic head
  remains `0014_buddy_chat_persistence`.
- **Non-goals:** Unmatch/End Buddy/Delete relationship.


## Cross-reference occurrences outside extracted headings

- Legacy line 6876: | BUDDY-002 (**Done 2026-10-01**) | Current Buddies API | BUDDY-001, INV-005 | All ACTIVE buddies with safe snapshots | Auth/privacy/query tests |
- Legacy line 6877: | BUDDY-003 (**Done 2026-10-01**) | Current Buddies UI | BUDDY-002, INV-007 | Multiple cards; Start Chatting; no Unmatch | UI/routing/a11y tests |
- Legacy line 6883: | ADMIN-V2-001 (**Done 2026-10-01**) | Monitoring APIs | INV-006, BUDDY-002 | Counts by invitation state, Buddy counts, zero-Buddy users | RBAC/aggregate/privacy tests |
- Legacy line 7601:   BUDDY-002 projection through a strict privacy-safe client contract and preserves server ordering
- Legacy line 7624: - **Dependencies / ownership:** BUDDY-002, INV-007; Frontend.
- Legacy line 7805: - **Dependencies / ownership:** INV-006, BUDDY-002, existing AUTH-018/EVT-008; Backend.
- Legacy line 8178: INV-005 → BUDDY-002
- Legacy line 8179: (BUDDY-002 + INV-007) → BUDDY-003
- Legacy line 8184: (INV-006 + BUDDY-002) → ADMIN-V2-001 → ADMIN-V2-002
- Legacy line 8209: 5. Complete \`INV-005\`, then branch to \`INV-006/007/009\`, \`BUDDY-002/003\`, \`CHAT-002..005\` and \`ADMIN-V2-001/002\` according to the graph.
- Legacy line 8219: - INV-008 can proceed after send; after INV-005, INV-006/007/009, BUDDY-002/003 and CHAT-002 may branch; CHAT-003/004 follows CHAT-002 and OPS-001.
