# CHAT-004

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** CHAT-003, BUDDY-003; Frontend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7749-7784

#### CHAT-004 — Accessible text chat frontend

- **Status:** **Done 2026-10-01.** The canonical `/user/buddy?conversation=<UUID>` locator now
  mounts a user/conversation-isolated private query and responsive text-chat surface. Initial and
  opaque-cursor older history remain chronological; older-page prepends preserve the visible scroll
  offset, authoritative IDs deduplicate REST/send/WebSocket/reconnect copies, and near-bottom
  auto-scroll never forces a reader away from older messages.
- **Implemented behavior:** The composer preserves exact plain text, validates nonblank and 10,000
  Unicode-code-point boundaries, assigns one UUID per logical send and reuses it across WS-first,
  timeout/close HTTP fallback and explicit retry. Pending/failed states reconcile only with a
  persisted server message. Bounded reconnect backoff refetches REST history after `chat.ready`;
  transport loss leaves HTTP chat usable. The latest rendered incoming boundary is acknowledged
  through CHAT-002 without acknowledging own messages or creating a client retention calculation.
- **Accessibility/privacy:** The page provides labeled log/composer/status regions, non-color sender
  labels, multiline keyboard behavior, visible focus, inert whitespace-preserving text, long-message
  wrapping, loading/empty/error/offline/new-message affordances and complete EN/DE copy. Socket URLs
  contain no token/query credential; message history is never persisted to browser storage. Logout,
  account switch, conversation switch, email change and authorization loss remove relevant private
  chat state.
- **Verification:** CHAT/BUDDY/auth targeted regressions pass 100 tests and the full frontend suite
  passes 656 tests. ESLint, strict TypeScript, Prettier, production Vite build and dependency audit
  pass; the audit gate upgraded only vulnerable transitive `brace-expansion` lock entries. Automated
  coverage includes cursor pagination, strict events, malicious text, 10k Unicode boundaries,
  double-submit prevention, stable retry identity, WS/HTTP reconciliation, duplicate fan-out,
  reconnect, first-read boundaries, authorization loss, route/email lock and state isolation. Local
  browser smoke proved the protected route redirects safely; authenticated two-participant browser
  acceptance was unavailable because no authenticated browser session/API was running and is not
  claimed as passed.
- **Purpose:** Provide the actual 1:1 conversation experience.
- **Scope / likely files:** chat page/route/client/hooks/components/locales; REST history + WSS state and read acknowledgement.
- **Dependencies / ownership:** CHAT-003, BUDDY-003; Frontend.
- **Security:** plain-text rendering, no HTML execution, no token URL/local persistence, verified lock and private cache cleanup.
- **Acceptance / DoD:** correct conversation from Buddy/email CTA; history, send/receive, optimistic state reconciliation, reconnect/catch-up, first-read update, expired-message absence and accessible announcements work.
- **Tests/gates:** component/a11y, malicious text, reconnect/duplicate event, logout/email-change lock and browser E2E tests.
- **Non-goals:** attachments, media, calls, groups or permanent client archive.


## Cross-reference occurrences outside extracted headings

- Legacy line 6711: | Matching frontend | **REC-004, INV-007, BUDDY-003, CHAT-004 and ADMIN-V2-002 implemented** | \`/user/matching\` consumes the strict privacy-safe recommendation, invitation and Current Buddies contracts; \`/user/buddy?conversation=<UUID>\` uses the authorized text-chat UI; \`/admin/matching\` now provides read-only aggregate, participant and safe-detail monitoring over the ADMIN-V2-001 APIs. | Reuse these sections unchanged in Semester work; neither the chat nor Admin UI creates or mutates a Buddy relationship or invitation. |
- Legacy line 6881: | CHAT-004 (**Done 2026-10-01**) | Text chat frontend | CHAT-003, BUDDY-003 | History/send/receive/read/reconnect; safe text rendering | UI/e2e/a11y tests |
- Legacy line 8182: (CHAT-003 + BUDDY-003) → CHAT-004
- Legacy line 8224: Final integration convergence: EMAIL-005 + PREF-004 + PROFILE-V2-002 + REC-004 + INV-007/008/009 + BUDDY-003 + CHAT-004/005 + ADMIN-V2-002 + SEM-007 + OPS-003 must all pass before ACCEPT-001.
- Legacy line 8244: The **second mandatory staging milestone** is after the complete user vertical slice **through PROFILE-V2-002 and CHAT-004 plus INV-008/009 and ADMIN-V2-002**. It validates two real verified users from recommendation through invitation/email/Accept/Current Buddies/chat, including exact invitation boundaries and the post-Accept type lock. Staging remains incomplete until **SEM-007 + CHAT-005 + OPS-003** and ACCEPT-001 prove reset/backup/restore/blocking and retention.
- Legacy line 8294: | **STAGING** | **OPS-002 AND OPS-003 DONE** | Early infrastructure, restore/migration, Edge/Cron A–F, real verification acceptance and primary/backup alert routing passed. The implemented PROFILE-V2-002 + CHAT-004 + INV-008/009 + ADMIN-V2-002 vertical slice still needs staging acceptance; release-candidate staging requires SEM-007 and ACCEPT-001. |
