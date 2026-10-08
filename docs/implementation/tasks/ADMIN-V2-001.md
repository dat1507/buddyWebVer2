# ADMIN-V2-001

**Control-plane status:** DONE / PRESERVED
**Track:** admin
**Priority:** -
**Dependencies (latest extracted):** INV-006, BUDDY-002, existing AUTH-018/EVT-008; Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7798-7810

#### ADMIN-V2-001 — Matching monitoring and safe participant APIs

- **Status:** **DONE 2026-10-01.** ADMIN-only `GET /api/admin/matching/stats`, `/participants` and `/participants/{profile_id}` expose read-only operational monitoring with private/no-store responses. Stats include participant/verified/zero-Buddy totals, effective invitation totals across every state and authoritative ACTIVE Match count. Participant pages expose only public profile identity, current active/verification/opt-in state and ACTIVE Buddy count; bounded `page`/`page_size` plus `student_type`, `verified` and `zero_buddies_only` filters use deterministic ordering. Audited detail reuses the existing privacy-safe batched profile/preference projection.
- **Security / query evidence:** current persisted ADMIN RBAC is the server authority; USER and anonymous callers are rejected before monitoring queries. Matching DTOs contain no email address, User ID, password/auth/session/token fields, normalized preference keys, storage internals, invitation messages or chat content. Aggregate/list queries use fixed batched `UNION ALL`/`GROUP BY` projections, exclude soft-deleted users/profiles/relationships, preserve inactive participants as explicit operational state and avoid N+1. Existing indexes are reused; no mutation route, migration or speculative index was added.
- **Verification:** targeted ADMIN matching plus Admin RBAC/audit, effective invitation expiry, recommendation projection and Current Buddies regressions passed (`124 passed`). The full backend suite passed (`1213 passed, 33 skipped`); the known WebSocket teardown flake did not occur in this single final run. Ruff, scoped format, strict mypy over 239 source files, sdist/wheel build, `pip check`, dependency audit, Alembic history/single head and Docker Compose validation passed. Alembic remains `0016_chat_message_cleanup`; no database change was required.
- **Purpose:** Give Admin operational visibility without decision power.
- **Scope / likely files:** admin matching schemas/services/router for participants, verified count, invitation state totals, ACTIVE Match total, Buddy count per user and zero-Buddy users.
- **Dependencies / ownership:** INV-006, BUDDY-002, existing AUTH-018/EVT-008; Backend.
- **Security:** ADMIN-only, paginated bounded safe projection, audited sensitive detail reads, no email in matching-safe response unless existing user-management endpoint explicitly requires it.
- **Acceptance / DoD:** counts reconcile to DB states including effective expiry; USER gets 403; no run/publish/override/respond mutation exists; multiple-Buddy counts are correct.
- **Tests/gates:** RBAC, aggregate fixtures, expiration, privacy/pagination/query tests.
- **Non-goals:** approving, activating, declining or manually changing a relationship.


## Cross-reference occurrences outside extracted headings

- Legacy line 4327: Superseded: ADMIN-014          Use Part 26 ADMIN-V2-001/002 monitoring
- Legacy line 6711: | Matching frontend | **REC-004, INV-007, BUDDY-003, CHAT-004 and ADMIN-V2-002 implemented** | \`/user/matching\` consumes the strict privacy-safe recommendation, invitation and Current Buddies contracts; \`/user/buddy?conversation=<UUID>\` uses the authorized text-chat UI; \`/admin/matching\` now provides read-only aggregate, participant and safe-detail monitoring over the ADMIN-V2-001 APIs. | Reuse these sections unchanged in Semester work; neither the chat nor Admin UI creates or mutates a Buddy relationship or invitation. |
- Legacy line 6718: | Admin auth/user views/audit | **ADMIN-V2-001/002 matching monitoring implemented; reset work remains** | Admin CLI, persisted-role protection, \`/api/admin/users\`, audited detail/photo reads and the read-only matching monitoring APIs/UI exist. Matching detail reads are audited; matching-safe DTOs and the private-cache UI omit email, User identity and communication content. Audit log remains append-only and Admin-linked with \`ON DELETE RESTRICT\`. | Reuse RBAC, safe projections, fixed-query aggregates, redaction and session cache clearing in Semester work. Semester reset still needs its dedicated operation audit that survives student deletion. |
- Legacy line 6883: | ADMIN-V2-001 (**Done 2026-10-01**) | Monitoring APIs | INV-006, BUDDY-002 | Counts by invitation state, Buddy counts, zero-Buddy users | RBAC/aggregate/privacy tests |
- Legacy line 6884: | ADMIN-V2-002 (**Done 2026-10-02**) | Monitoring UI | ADMIN-V2-001, ADMIN-003/004 | No run/publish/override controls | UI/RBAC/a11y tests |
- Legacy line 7817:   \`student_type\`, \`verified\` and \`zero_buddies_only\` filters to ADMIN-V2-001. Audited participant
- Legacy line 7835: - **Dependencies / ownership:** ADMIN-V2-001, ADMIN-003/004; Frontend.
- Legacy line 8184: (INV-006 + BUDDY-002) → ADMIN-V2-001 → ADMIN-V2-002
- Legacy line 8209: 5. Complete \`INV-005\`, then branch to \`INV-006/007/009\`, \`BUDDY-002/003\`, \`CHAT-002..005\` and \`ADMIN-V2-001/002\` according to the graph.
- Legacy line 8293: | **LOCAL** | **NOT READY (V2)** | CHAT-001..005 and ADMIN-V2-001/002 monitoring are code-complete with automated gates; authenticated two-participant browser acceptance plus Semester/reset/full vertical flows are still outstanding. |
