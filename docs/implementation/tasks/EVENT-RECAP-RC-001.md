# EVENT-RECAP-RC-001 — approved Recap release preparation

DONE - LOCAL PREPARATION COMPLETE / PUBLICATION BLOCKED / PRODUCTION NO-GO. Owner assignment 2026-11-03. Freeze accepted `bdcd082aee5c15944bfa0f4060d9219c731062d9`;
8/8 UI categories owner PASS. No redesign or second UI approval unless confirmed regression demands it.
Integration branch `codex/events-recap-rc`, base freshly fetched `6851725362184af7c85828602b6c881f64374b60`.

## Authorized scope

1. Merge the approved history locally; preserve every newer main fix, security dependency and existing
   worktree/unpublished branch. Inspect conflicts and prove approved recap UI/newer Admin labels retained.
2. Disposable fresh and actual Production 0021 → 0022 → 0023 migration tests; one head, version capacity,
   constraints/indexes/FKs, private grants/RLS, old deployed backend compatibility and recovery strategy.
3. Full final-candidate frontend/backend CI-equivalent gates and dependency audits; no unreported failure
   or new skip. Local real API tests for auth/CSRF/visibility/ownership/versions/retry/media/cleanup/images.
4. Read-only provider metadata, quota/capacity/backup checks. Unknowns stay UNVERIFIED or OWNER ACTION
   REQUIRED. Preserve short signed-URL expiry limitation; first 10–30 Recap resource forecast.
5. Exact source/commit/file manifest; rollout/rollback/activation and Preview isolation plan. Separate
   READY FOR HOSTED CI from Production GO. No paid infrastructure, provider settings or Production writes.
6. Commit locally, update handoff/control/index/dated observations and Project Knowledge. Stop before push;
   request specific candidate-only publication approval only if trigger safety is established.

## Initial verified observations

- Approved feature HEAD exact, clean; latest origin/main exact 6851725 after fetch.
- Four intervening main commits: existing chatbot integration/docs, then two Admin action-label fixes.
  Preserve them as current main baseline; do not activate chatbot or include later unpublished work.
- Production read-only Alembic scalar: `0021_restore_runtime_permissions`.
- Supabase organization Free. Object metadata aggregates: event-media 4 objects/964762 bytes,
  profile-images 5 objects/1013678 bytes. This is current object metadata, not billed quota/egress.
- Vercel connector detailed project request403: team access missing. Dashboard fallback read-only.
- Merge conflicts: main.py import adjacency and four documentation prepend conflicts; retain both
  source imports and all dated history. App/locales/Admin list auto-merge; inspect conservatively.

## Focused paths

Approved `EVENT-RECAP-001` task/source/tests plus shared App/main.py/Admin Events/locales, Alembic,
Dockerfile/package/locks/CI and linked release/backup records. Do not read the legacy archive end-to-end.

## Completion - 2026-11-04

Tested source merge e77d7182c30397c134c939b1057d3d73b41d675d; final documentation/test-only successor
contains the exact manifest. [Assessment](../../project-knowledge/frontend/EVENT_RECAP_PRE_RELEASE_2026-11-04.md)
and [file/commit/evidence manifest](../../project-knowledge/frontend/EVENT_RECAP_RC_MANIFEST_2026-11-04.json).
Frontend925/94 files PASS; backend1868 PASS/37 unchanged opt-in skips; mypy328, lint/format/types,
production builds/image/wheel, migrations/API12, commit recovery3, runtime audits and Compose PASS.
Existing dev npm audit FAIL:14 moderate transitive entries/one advisory; no new waiver granted.
Approved UI/locales/source, current Admin labels and main chatbot/locks preserved. Exact deployed
c0687ba works pre-activation on upgraded local schema; linked Event DELETE500 confirms rollback
write-freeze/forward-repair requirement. Constrained local pressure:282.8MiB RSS, no OOM, busy429,
but auth/Events reads6.7-10.6s; Production capacity remains UNVERIFIED.
Backup/restore, quotas, Preview target/isolation, exact hosted CI/browser and all Production approvals
remain owner gates. Public Recap activates with frontend deployment; no dedicated public flag.
No push/deploy/Production migration/data/configuration/subscription change. Clear TASK_ID; do not
start unrelated READY follow-ups. Publication approval is requested only after trigger/isolation
safety is verified. Frozen approved feature and original dirty checkout remain preserved.
