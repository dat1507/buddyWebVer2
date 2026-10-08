# BUDDY-003

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** BUDDY-002, INV-007; Frontend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7598-7629

#### BUDDY-003 — Current Buddies UI and route compatibility

- **Status:** **Done 2026-10-01.** `/user/matching#current-buddies` now reads the owner-only
  BUDDY-002 projection through a strict privacy-safe client contract and preserves server ordering
  with bounded load-more pagination and duplicate suppression. Zero/one/many, initial loading,
  refresh, empty, sanitized error/retry, end-of-results and VERIFIED-lock states are distinct.
  Cards reuse the signed-avatar fallback, safe profile/preference/availability rendering and the
  persisted compatibility explanation; they never recompute scoring or render contact/internal
  fields. Active relationships remain visible to a verified USER when new matching is opted out.
  Each Start Chatting link carries only its exact opaque conversation UUID on the approved
  `/user/buddy?conversation=...` path. That route fail-closes malformed/additional state and
  deterministically redirects to/focuses the canonical Current Buddies section, auto-loading later
  pages when needed; the conversation locator never grants authorization. No Unmatch/End/Delete
  relationship control or chat transport/history UI was added. Current Buddy queries remain under
  the existing private `matching` cache root, are invalidated after invitation transitions and are
  removed on logout/account switch.
- **Verification:** BUDDY/matching/auth targeted tests pass (121), focused navigation/readiness
  regressions pass (20), and the full frontend suite passes (641). Prettier, ESLint, strict
  TypeScript, production Vite build and the production dependency audit (zero vulnerabilities)
  pass. Browser smoke verified meaningful rendering, no Vite overlay/console error/horizontal
  overflow, canonical protected deep-link preservation, malformed-link fail-closed behavior and
  768 px/390 px layouts. Authenticated real-user card acceptance was not claimed because no browser
  test account/session was available. No backend, schema, migration or dependency change was
  required; Alembic head remains `0014_buddy_chat_persistence`.
- **Purpose:** Present multiple relationships and preserve the existing navigation surface.
- **Scope / likely files:** Current Buddies matching-page section; `/user/buddy` redirect/focus behavior; cards and Start Chatting action.
- **Dependencies / ownership:** BUDDY-002, INV-007; Frontend.
- **Security:** use only safe DTO; clear cache on logout; no hidden contact fields.
- **Acceptance / DoD:** accessible zero/one/many states; availability/shared explanation display; Start Chatting opens exact match conversation; no Unmatch/End/Delete Buddy control exists.
- **Tests/gates:** routing, component/a11y, multi-Buddy and verification-lock tests.
- **Non-goals:** separate Buddy data store or relationship mutation.


## Cross-reference occurrences outside extracted headings

- Legacy line 4326: Superseded: FE-037             Use Part 26 BUDDY-003 route-compatible Current Buddies
- Legacy line 6711: | Matching frontend | **REC-004, INV-007, BUDDY-003, CHAT-004 and ADMIN-V2-002 implemented** | \`/user/matching\` consumes the strict privacy-safe recommendation, invitation and Current Buddies contracts; \`/user/buddy?conversation=<UUID>\` uses the authorized text-chat UI; \`/admin/matching\` now provides read-only aggregate, participant and safe-detail monitoring over the ADMIN-V2-001 APIs. | Reuse these sections unchanged in Semester work; neither the chat nor Admin UI creates or mutates a Buddy relationship or invitation. |
- Legacy line 6877: | BUDDY-003 (**Done 2026-10-01**) | Current Buddies UI | BUDDY-002, INV-007 | Multiple cards; Start Chatting; no Unmatch | UI/routing/a11y tests |
- Legacy line 6881: | CHAT-004 (**Done 2026-10-01**) | Text chat frontend | CHAT-003, BUDDY-003 | History/send/receive/read/reconnect; safe text rendering | UI/e2e/a11y tests |
- Legacy line 7779: - **Dependencies / ownership:** CHAT-003, BUDDY-003; Frontend.
- Legacy line 8179: (BUDDY-002 + INV-007) → BUDDY-003
- Legacy line 8182: (CHAT-003 + BUDDY-003) → CHAT-004
- Legacy line 8224: Final integration convergence: EMAIL-005 + PREF-004 + PROFILE-V2-002 + REC-004 + INV-007/008/009 + BUDDY-003 + CHAT-004/005 + ADMIN-V2-002 + SEM-007 + OPS-003 must all pass before ACCEPT-001.
