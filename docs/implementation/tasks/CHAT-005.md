# CHAT-005

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** CHAT-002, OPS-001; Backend + Infrastructure.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7785-7797

#### CHAT-005 — Expired-message cleanup job

- **Status:** **DONE 2026-10-01.** Migration `0016_chat_message_cleanup`, the cleanup service/CLI and the operations runbook implement one bounded transaction per invocation. The database owns the default cutoff through `statement_timestamp()`; candidates use the persisted effective `expires_at`, deterministic `(expires_at, id)` ordering and `FOR UPDATE ... SKIP LOCKED`. The default batch is 20, the maximum is 100, repeat/concurrent invocations are idempotent, and the command performs no external I/O or in-process scheduling.
- **Security / operations evidence:** the `SECURITY DEFINER` function has an empty `search_path`, schema-qualified objects and function-only runtime execution; direct runtime `DELETE` on `buddy_messages` remains denied. Public/data-API execution is revoked, the existing expiry index is reused, telemetry is aggregate/redacted, and the runbook assigns cadence to the existing external deployment scheduler rather than adding a second scheduler.
- **Verification:** targeted CHAT-005 coverage passed (30 tests including the PostgreSQL live suite). Disposable PostgreSQL 17 proved `<`/`=`/`>` cutoff behavior, first-read shortened expiry, deterministic bounded progress, zero-row retry, disjoint concurrent workers, rollback/resume, database-clock default, future-cutoff rejection, API effective-expiry protection, relationship/conversation preservation, function allowance plus direct-delete denial, and upgrade/downgrade/re-upgrade with one head and no schema drift. Ruff, mypy, package build, `pip check`, dependency audit and Compose validation passed. The full backend result was `1192 passed, 33 skipped, 1 failed`: the sole failure is the pre-existing nested Starlette WebSocket TestClient teardown flake in `test_websocket_two_participant_fanout_is_safe_idempotent_and_isolated`; three fresh isolated processes produced PASS/PASS/FAIL, confirming nondeterministic teardown behavior outside CHAT-005 source and scope.
- **Purpose:** Enforce retention physically without relying on clients.
- **Scope / likely files:** worker/scheduler cleanup service/command, batch/lease metrics and runbook.
- **Dependencies / ownership:** CHAT-002, OPS-001; Backend + Infrastructure.
- **Security:** exact server-time predicate, bounded batches, idempotency, least-privilege delete and redacted metrics.
- **Acceptance / DoD:** expired messages are hard-deleted; non-expired rows are untouched; repeated/concurrent workers are safe; API filtering protects privacy if cleanup lags.
- **Tests/gates:** clock/boundary, batch/concurrency, failure resume and disposable DB tests.
- **Non-goals:** deleting conversations/Matches or manual user history deletion.


## Cross-reference occurrences outside extracted headings

- Legacy line 6882: | CHAT-005 (**Done 2026-10-01**) | Message cleanup job | CHAT-002, OPS-001 | Hard-delete expired; API never returns expired | Clock/job/idempotency tests |
- Legacy line 8132: - **Dependencies / ownership:** EMAIL/PREF/PROFILE/REC/INV/BUDDY/CHAT/ADMIN V2 tasks, SEM-007, CHAT-005, OPS-003; QA + Product + Engineering + Operations.
- Legacy line 8183: (CHAT-002 + OPS-001) → CHAT-005
- Legacy line 8196: All functional branches + CHAT-005 + ADMIN-V2-002 + SEM-007 + OPS-003
- Legacy line 8244: The **second mandatory staging milestone** is after the complete user vertical slice **through PROFILE-V2-002 and CHAT-004 plus INV-008/009 and ADMIN-V2-002**. It validates two real verified users from recommendation through invitation/email/Accept/Current Buddies/chat, including exact invitation boundaries and the post-Accept type lock. Staging remains incomplete until **SEM-007 + CHAT-005 + OPS-003** and ACCEPT-001 prove reset/backup/restore/blocking and retention.
