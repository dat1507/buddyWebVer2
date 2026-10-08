# Documentation migration validation

**Migration date:** 2026-10-08

## Required invariants

- `AGENTS.md`, `SESSION_HANDOFF.md` and root `implementation-plan.md` exist.
- Every recognized Task ID in the legacy plan has a matching
  `docs/implementation/tasks/<TASK_ID>.md` extract and an entry in `task-index.md`.
- The lightweight plan links only to existing documentation paths.
- The legacy plan remains byte-complete except for the already-present current release-boundary note
  and the archive pointer added by this migration; pre-existing user documentation edits remain.
- No file under `apps/`, `supabase/` or application runtime configuration changes.
- No secret-like value is introduced.
- Markdown links and Task ID paths resolve.
- Production status distinguishes direct public checks, retained operator evidence and unverified
  authenticated smoke.
- `git diff --check` passes.

## Validation record

Validation performed against the refactored worktree:

| Check | Result |
| --- | --- |
| Legacy plan before refactor | 677,480 bytes; 9,181 lines |
| Legacy archive after pointer | 677,868 bytes; 9,186 lines |
| New lightweight plan | 8,246 bytes; 139 lines |
| Extracted Task IDs/files | 212 / 212 |
| Task extract payload | 939,196 bytes, split by Task ID |
| Missing/extra Task files | 0 / 0 |
| Missing task-index entries | 0 |
| Broken local links in the new documentation set | 0 |
| Application/source/config changes | 0 |
| Secret-pattern hits in the new documentation set | 0 |

Status distribution: 152 DONE/PRESERVED, 1 IN PROGRESS/READY, 1 OPEN hardening, 13 deferred
post-deployment, 15 planned backlog, 26 superseded and 4 requiring a new contract.

Final whitespace, staged-diff, repository-status and commit checks are run after this record is
written. The final commit identifier is reported in the handoff response because a Git commit cannot
contain its own resulting hash.

## Result

**PASS.** Task coverage, current-status reconciliation, path resolution, source-scope, secret scan,
unstaged-diff check and staged `git diff --check` all passed. The documentation commit is the only
remaining handoff action.
