# BuddyWebv2 agent instructions

These instructions apply to the entire repository.

## Minimal reading protocol

1. Read `SESSION_HANDOFF.md` first.
2. Read the root `implementation-plan.md` control plane.
3. If `SESSION_HANDOFF.md` declares a `TASK_ID`, read only:
   - `docs/implementation/tasks/<TASK_ID>.md`;
   - the source files and focused tests named by that task;
   - any explicitly linked current decision or operations record.
4. If no task is assigned, use the READY/IN PROGRESS table in `implementation-plan.md` and report
   the highest-priority executable task. Do not start it without the user's instruction.
5. Do not read `implementation_plan_vgu_buddy.md` end to end. It is the immutable legacy archive.
   Use `docs/implementation/task-index.md` to locate one task-specific extract when historical detail
   is genuinely required.

## Source-of-truth precedence

When documents conflict, use this order:

1. A newer directly verified environment observation recorded in
   `docs/implementation/production-status.md`.
2. `SESSION_HANDOFF.md` for the current task boundary and verified continuation point.
3. `implementation-plan.md` for status, priority and execution order.
4. The matching task extract in `docs/implementation/tasks/` for dependencies, acceptance criteria,
   technical requirements and preserved history.
5. `docs/implementation/decision-log.md` and current dated operations records.
6. `implementation_plan_vgu_buddy.md` only as a legacy archive.

Never use an older `Next task`, `NOT READY`, deployment, DNS or blocker statement from the archive
when a newer control-plane or production-status record supersedes it.

## Execution constraints

- Preserve user changes already present in a dirty worktree. Inspect `git status` and overlapping
  diffs before editing.
- Do not repeat a gate explicitly recorded as PASS unless the selected task requires regression
  verification for a new change.
- Do not mutate Production, databases, DNS, provider configuration, secrets or user accounts without
  a separate explicit request. Public read-only health/DNS checks are diagnostic only.
- Never place secrets, credentials, private URLs, tokens or personal test-account data in Git, chat,
  command arguments, process listings or evidence.
- Keep completed task history immutable. Correct it only with newer evidence and an explicit note.
- Respect superseded/recontract-required statuses in `implementation-plan.md`; a historical contract
  is not authorization to implement it.
- Application source changes require an assigned implementation task. Documentation-only work must
  not change `apps/`, `supabase/`, runtime configuration, database state or Production.
- Use direct-to-main only while that remains the repository's documented workflow; do not create a
  branch or PR unless the user asks.

## Documentation maintenance

After any task completion or environment acceptance:

1. Update the task extract and `implementation-plan.md` status.
2. Update `SESSION_HANDOFF.md` with the last verified continuation point and clear/set `TASK_ID`.
3. Update `docs/implementation/production-status.md` only from dated evidence.
4. Regenerate or validate `docs/implementation/task-index.md` and task-path coverage.
5. Preserve the legacy archive; do not append routine session logs to it.

Validation commands and invariants are documented in `docs/implementation/validation.md`.
