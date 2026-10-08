# CHAT-003

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** CHAT-002, OPS-001; Backend + Infrastructure.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7712-7748

#### CHAT-003 — Authenticated FastAPI WebSocket and Redis Pub/Sub

- **Status:** **DONE — 2026-10-01.** Exact route
  `WS /api/ws/chat/{conversation_id}` accepts only the strict `message.send` event with
  `client_message_id` and plain `body`. The Origin must exactly match the configured credentialed
  allowlist; identity comes only from the signed access cookie and current VERIFIED USER/profile;
  the opaque locator is re-authorized against its ACTIVE Match before subscribe and again for
  every inbound send/outbound delivery.
- **Persistence and fan-out:** WebSocket send reuses CHAT-002 validation, sender derivation,
  idempotency and PostgreSQL transaction. Only after commit does a server-owned Redis channel
  publish the persisted message ID. Each worker/subscriber reloads the effective message through
  PostgreSQL and emits the same privacy-safe CHAT-002 DTO from its recipient's perspective. A
  cluster-slot-safe Lua publish/dedupe marker prevents immediate retry echoes without making Redis
  durable; channel names contain neither message bodies nor participant identity.
- **Failure/recovery:** Redis subscription failure rejects the upgrade with safe `1013`; publish
  failure after commit returns a persisted-but-realtime-unavailable acknowledgement and closes for
  REST recovery without rolling back or duplicating the row. Reconnect emits no synthetic Redis
  history: CHAT-002 cursor history is the explicit gap-recovery path. Direct bounded socket writes,
  a five-second slow-client deadline, 128-KiB client-event ceiling, Redis pull consumption and
  deterministic unsubscribe/task cancellation avoid unbounded queues and leaked subscriptions.
  Unsupported/binary/oversized/malformed events, rate-limit failures and idempotency conflicts use
  stable sanitized events/close codes; read acknowledgement remains the CHAT-002 HTTP endpoint.
- **Verification/security:** Actual FastAPI WebSocket + disposable PostgreSQL/Redis acceptance
  proves commit-before-publish, two-participant delivery, separate-connection multi-worker fan-out,
  conversation isolation, sender derivation, exact retry convergence, outsider/unverified denial,
  reconnect ephemerality, cleanup and REST history recovery. Unit/integration coverage includes
  exact Origin/cookie policy, no query-token auth, strict schemas, Redis connect/publish outage,
  safe DTO/log allowlists, rate limits and CHAT-001/002 regressions. No database migration,
  frontend, presence, typing/read-receipt event or Supabase Realtime behavior was added.
- **Purpose:** Deliver realtime messages across backend workers while retaining REST recovery.
- **Scope / likely files:** async Redis config/client, WebSocket router/connection manager, origin/session authorization and publish/subscribe adapter; backend host/deployment docs.
- **Dependencies / ownership:** CHAT-002, OPS-001; Backend + Infrastructure.
- **Security:** cookie session handshake, exact Origin allowlist, current DB VERIFIED/ACTIVE participation, message/rate limits, reauthorization on reconnect/state change, no URL tokens.
- **Acceptance / DoD:** two participants receive committed messages through WSS; outsider/unverified rejected; multi-worker delivery uses Redis; Redis outage degrades safely without losing committed DB messages; reconnect catches up via REST.
- **Tests/gates:** WebSocket auth/origin, Redis integration/TLS config, two-worker pub/sub, disconnect/reconnect and outage tests.
- **Non-goals:** Supabase Realtime, presence guarantees or typing indicators.


## Cross-reference occurrences outside extracted headings

- Legacy line 6715: | Redis | **Implemented foundation + CHAT-003 Pub/Sub** | Auth rate limits retain their Redis backend; Docker Compose supplies loopback-only Redis; the server-only async boundary enforces environment prefixes/production \`rediss://\`; CHAT-003 adds conversation-isolated ID-only Pub/Sub with bounded socket consumption and distributed retry dedupe. | Redis remains ephemeral fan-out, never durable chat history. Reuse the shared pool/TLS configuration for later coordination. |
- Legacy line 6880: | CHAT-003 (**Done 2026-10-01**) | WebSocket + Redis realtime | CHAT-002, OPS-001 | Authenticated WSS, Redis Pub/Sub, reconnect recovery | Integration/multi-worker/security tests |
- Legacy line 6881: | CHAT-004 (**Done 2026-10-01**) | Text chat frontend | CHAT-003, BUDDY-003 | History/send/receive/read/reconnect; safe text rendering | UI/e2e/a11y tests |
- Legacy line 7703:   frontend chat and physical cleanup remain owned by CHAT-003/004/005.
- Legacy line 7779: - **Dependencies / ownership:** CHAT-003, BUDDY-003; Frontend.
- Legacy line 7885:   pass. The complete backend suite passes with 1,241 passed, 35 skipped and the pre-existing CHAT-003
- Legacy line 7947:   35 skipped; its only failure was the documented unrelated CHAT-003 WebSocket teardown
- Legacy line 7992:   failure was the documented unrelated CHAT-003 Starlette WebSocket teardown \`CancelledError\`, and
- Legacy line 8033:   backend suite produced 1,301 passed and 37 skipped; the known CHAT-003 teardown flake did not occur.
- Legacy line 8068:   failure was the documented unrelated CHAT-003 Starlette WebSocket teardown \`CancelledError\`, which
- Legacy line 8181: (CHAT-002 + OPS-001) → CHAT-003
- Legacy line 8182: (CHAT-003 + BUDDY-003) → CHAT-004
- Legacy line 8219: - INV-008 can proceed after send; after INV-005, INV-006/007/009, BUDDY-002/003 and CHAT-002 may branch; CHAT-003/004 follows CHAT-002 and OPS-001.
