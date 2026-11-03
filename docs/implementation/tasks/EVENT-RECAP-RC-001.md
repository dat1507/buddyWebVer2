# EVENT-RECAP-RC-001 — approved Recap release preparation

IN PROGRESS. Owner assignment 2026-11-03. Freeze accepted `bdcd082aee5c15944bfa0f4060d9219c731062d9`;
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
