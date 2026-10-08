# CHAT-002

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** CHAT-001, AUTH-V2-001; Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7674-7711

#### CHAT-002 — Authorized history, send fallback and first-read retention

- **Status:** **DONE — 2026-10-01.** The exact API contract uses opaque `conversation_id`
  locators for `GET/POST /api/chat/conversations/{conversation_id}/messages` and
  `POST /api/chat/conversations/{conversation_id}/messages/read`; every operation re-derives the
  current VERIFIED USER's participation in the exact ACTIVE Match.
- **Implementation:** History uses a server-issued opaque `before` cursor over the complete
  `(created_at, id)` tuple, fetches the newest window/default 50/max 100 and returns each page in
  chronological order. Every read filters `expires_at <= server_now` before cleanup. HTTP send
  derives its sender from the authenticated principal, reuses the CHAT-001 plain-text/nonblank/
  10,000-code-point contract, and is protected by the shared CSRF and per-user/IP rate-limit
  infrastructure. Migration `0015_chat_send_idempotency` adds only `client_message_id`, backfills
  legacy rows from their server ID and enforces unique `(sender_id, client_message_id)`; an exact
  conversation/body replay returns the same row while mismatched reuse returns sanitized `409`.
- **First-read retention:** The explicit `through_message_id` acknowledgement performs one
  conditional PostgreSQL `UPDATE` of only unread, non-expired incoming rows at or before the
  authorized `(created_at, id)` boundary. It writes the first server timestamp once and sets
  `expires_at=LEAST(existing_expires_at, read_at+30d)`, which is equivalent to the confirmed
  `min(read+30d, created+90d)` invariant and can never extend retention. Sender-owned or newer
  messages are not marked read.
- **Security/verification:** Responses expose only opaque message ID, `self|buddy`, plain body and
  created/read timestamps; they exclude User IDs, email, Match/invitation/schema fields,
  idempotency keys and retention internals. IDOR/missing/inactive paths are sanitized and private
  responses are `private, no-store`. Isolated PostgreSQL acceptance proves concurrent first-read,
  repeated-read immutability, 30/90-day cap, concurrent idempotent send, mismatch conflicts,
  same-timestamp ordering, effective expiry, A-B/A-C isolation, outsider denial, least-privilege
  grant, migration backfill, upgrade/downgrade/re-upgrade and autogenerate drift. Relevant
  CHAT/BUDDY/auth regression and the full backend suite pass; Ruff, strict mypy, package build,
  pip check/audit, Alembic graph and Docker Compose validation pass. WebSocket/Redis realtime,
  frontend chat and physical cleanup remain owned by CHAT-003/004/005.
- **Purpose:** Make PostgreSQL the complete recoverable chat authority.
- **Scope / likely files:** chat schemas/services/HTTP routes, cursor pagination, send/read transactions and retention helper.
- **Dependencies / ownership:** CHAT-001, AUTH-V2-001; Backend.
- **Security:** VERIFIED ACTIVE participant only; per-user send rate/size limits; safe text; expired predicate applied in every read; no foreign match enumeration.
- **Acceptance / DoD:** ordered pagination and idempotent send key; first recipient read sets `read_at` once and `expires_at=min(read+30d, created+90d)`; never-read expires at +90d; later reads never extend retention.
- **Tests/gates:** frozen-clock formula, sender-vs-recipient, pagination, IDOR, rate, duplicate send and expired-filter tests.
- **Non-goals:** realtime transport or frontend.


## Cross-reference occurrences outside extracted headings

- Legacy line 6714: | Chat/realtime | **CHAT-001..005 persistence, HTTP recovery, authenticated realtime, accessible frontend and expired-message cleanup implemented** | Migrations \`0014_buddy_chat_persistence\`/\`0015_chat_send_idempotency\` provide authoritative chat storage and send idempotency; \`0016_chat_message_cleanup\` adds the bounded least-privilege cleanup function. CHAT-002 REST recovery, \`WS /api/ws/chat/{conversation_id}\`, the \`/user/buddy\` UI and the cleanup CLI cover participant-authorized history, cursor pagination, idempotent send, first-read retention, multi-worker fan-out/reconciliation and physical expiry enforcement. PostgreSQL remains authoritative. | Reuse these contracts in ADMIN/Semester work; Redis/WebSocket remain delivery-only, the frontend stores no durable message archive and the deployment scheduler invokes only the documented cleanup command. |
- Legacy line 6879: | CHAT-002 (**Done 2026-10-01**) | History/read/retention service | CHAT-001, AUTH-V2-001 | Participant-only cursor history; idempotent send; atomic first-read retention formula | API/time/auth/PostgreSQL race tests |
- Legacy line 6880: | CHAT-003 (**Done 2026-10-01**) | WebSocket + Redis realtime | CHAT-002, OPS-001 | Authenticated WSS, Redis Pub/Sub, reconnect recovery | Integration/multi-worker/security tests |
- Legacy line 6882: | CHAT-005 (**Done 2026-10-01**) | Message cleanup job | CHAT-002, OPS-001 | Hard-delete expired; API never returns expired | Clock/job/idempotency tests |
- Legacy line 7664:   head is \`0014_buddy_chat_persistence\`. CHAT-002 retains ownership of HTTP history/send/read,
- Legacy line 7720: - **Persistence and fan-out:** WebSocket send reuses CHAT-002 validation, sender derivation,
- Legacy line 7723:   PostgreSQL and emits the same privacy-safe CHAT-002 DTO from its recipient's perspective. A
- Legacy line 7729:   history: CHAT-002 cursor history is the explicit gap-recovery path. Direct bounded socket writes,
- Legacy line 7733:   stable sanitized events/close codes; read acknowledgement remains the CHAT-002 HTTP endpoint.
- Legacy line 7743: - **Dependencies / ownership:** CHAT-002, OPS-001; Backend + Infrastructure.
- Legacy line 7761:   through CHAT-002 without acknowledging own messages or creating a client retention calculation.
- Legacy line 7792: - **Dependencies / ownership:** CHAT-002, OPS-001; Backend + Infrastructure.
- Legacy line 8180: (CHAT-001 + AUTH-V2-001) → CHAT-002
- Legacy line 8181: (CHAT-002 + OPS-001) → CHAT-003
- Legacy line 8183: (CHAT-002 + OPS-001) → CHAT-005
- Legacy line 8209: 5. Complete \`INV-005\`, then branch to \`INV-006/007/009\`, \`BUDDY-002/003\`, \`CHAT-002..005\` and \`ADMIN-V2-001/002\` according to the graph.
- Legacy line 8219: - INV-008 can proceed after send; after INV-005, INV-006/007/009, BUDDY-002/003 and CHAT-002 may branch; CHAT-003/004 follows CHAT-002 and OPS-001.
