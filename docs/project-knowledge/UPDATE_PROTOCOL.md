# Incremental knowledge-base update protocol

Last audited source commit: `794a1a4530f3770f4e67b2863ebf658c8c0078d2`.
Machine-readable checkpoint: [AUDIT_BASELINE.json](AUDIT_BASELINE.json).
This points to the source being audited, not the future documentation commit, avoiding a
self-referential SHA. Audit date and verification scope belong in the checkpoint.

## Start with a bounded delta

Follow AGENTS/handoff and the current assigned task. Do not preload every knowledge document.
Read this protocol, the checkpoint and only the category affected by the task.

```sh
git status --short
git log --oneline <last-audited-sha>..HEAD
git diff --stat <last-audited-sha>..HEAD
git diff --name-status <last-audited-sha>..HEAD
```

Confirm the checkpoint is an ancestor of HEAD. If it is not, inspect both sides of the merge
base and explicitly document the divergence; never silently advance over an unaudited lane.
Inspect overlapping dirty changes before editing. For uncommitted work, review the working
diff separately; a SHA checkpoint cannot certify uncommitted files.

## Map changes to documentation

| Changed area                       | Usually update                                                             |
| ---------------------------------- | -------------------------------------------------------------------------- |
| Route, component, UI state, locale | frontend; affected workflow only                                           |
| API/schema/service/domain rule     | backend plus affected workflow; security if authority changes              |
| Model/migration/retention          | database; migration inventory; workflow integrity rules                    |
| Worker/provider/release topology   | infrastructure; dated evidence remains in operations/Production status     |
| Auth/permission/private response   | security; focused backend/frontend references                              |
| Meaningful test strategy/gate      | testing; reference task validation rather than copying counts everywhere   |
| Root cause and resolution          | incidents, with symptom/cause/fix/verification confidence                  |
| Material design decision           | decisions; document known alternatives/trade-offs, label missing rationale |
| Cross-service boundary             | architecture/diagram only if the relationship materially changes           |

Spelling, formatting, asset alignment and small cosmetic changes generally need no new
milestone/ADR. Review them, classify as no knowledge impact, and record the reviewed range in
the checkpoint when the entire range has been examined. Do not rewrite whole guides for them.

## Write a small coherent update

Explain final behavior, source entry points, important invariants and acceptance limits.
Change the authoritative explanation once and cross-link it. Add a short changelog milestone
only for significant feature/architecture/operations evolution. Link the task and dated evidence
instead of copying logs. Keep code-confirmed, recorded acceptance, inferred and unknown claims
distinct. Do not turn an ancestor's inclusion in a deploy into independent feature acceptance.

Preserve completed task history. Correct conflicts with a newer dated note and evidence;
never overwrite old failure/rollback observations as if they had not occurred. Do not change
project-wide Agent instructions for routine knowledge maintenance.

## Validate and advance

1. Resolve relative Markdown links against their containing file; check file targets and
   heading anchors separately. Exclude URLs from local file resolution. Verify code paths,
   function names and significant SHA references against the reviewed source.
2. Check task-index set equality/uniqueness and legacy task-path coverage using the existing
   [validation invariants](../implementation/validation.md). Preserve the legacy archive.
3. Run `git diff --check` and focused Markdown/JSON formatting. Inspect the final diff for
   sensitive values, account details, signed/private links and unsupported runtime claims.
4. For docs-only work confirm no `apps/`, `supabase/`, runtime or deployment configuration
   delta. For a feature task retain its meaningful checks; do not rerun accepted gates for prose.
5. Update only affected knowledge files, the audit checkpoint, task extract, concise control
   plane and handoff. Update Production status only with new dated environment evidence.
6. Advance `last_audited_source_commit` to the reviewed HEAD only after the complete delta has
   been classified and required explanations verified. Record any inaccessible history as
   a gap rather than pretending it was audited. Regenerate the inventory only when docs/
   migrations/history scope changes; otherwise retain its original baseline label.

Git commands above are local reads. Commit/push/deployment remain subject to the current task's
authorization. The initial audit authorizes one docs-only local commit, with no push/deploy.

## Task completion checklist in one paragraph

Review the diff for knowledge impact, patch affected explanations, link the task/evidence,
validate links/scope/security, record the reviewed source SHA and leave a precise handoff.
If no technical meaning changed, record that classification without adding generic prose.
