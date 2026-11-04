# Events Recap Rolling 9 — controlled release checkpoint, 2026-11-04

LOCAL IMPLEMENTATION COMPLETE. Hosted publication waiting for current provider safety evidence.
Production NOT DEPLOYED / NOT VERIFIED / NO-GO. This record does not authorize exports or migrations.

## Candidate and behavior

Isolated branch `codex/events-recap-rolling9`, based on Rolling10
`f8e09ef9ba69f97c3bd5a2a81a178f263fde7918`. Fresh remote main remains
`6d32d1a86e2fb87d24990355a14db91eb867a03e`; its published Chatbot and Admin fixes are preserved.
Implementation SHA and final candidate SHA are reported in delivery; the final candidate includes
main ancestry. Existing branches, dirty primary worktree and recovery preparation are untouched.

Service overflow offset and public page size are nine. Publishing the tenth retains exactly nine
by original publication timestamp then UUID. Drafts excluded; edits/no-op retries never evict.
Publication, audit, hard metadata deletion and durable cleanup jobs remain atomic. Network cleanup
runs after commit; interrupted/failed deletion remains pending and retryable. Original Event,
Slider/profile images and unrelated objects remain protected. No automatic Archive/confirmation.
EN/DE warning says nine. Facebook target/safe external behavior remain unchanged; Facebook does
not receive copies of evicted images. Existing gallery CSS retains three desktop columns (nine
cards form 3x3), two below1024px and one below701px; no layout redesign.

## Migration decision

**No new migration. 0024 is byte-identical to the prior checkpoint.** Limit/page size are application
policy, not a schema constraint. Preserve its historical >10 legacy overflow guard/message/test;
rewriting a potentially published migration would damage history consistency. Before enabling the
new backend, read-only count active PUBLISHED Recaps and require <=9. If >9 exist, stop for an owner
reconciliation decision; do not delete content during migration. Isolated tests also prove repair
of an oversized synthetic set on the next new publication. Freeze legacy backend status writes
through the rollout; new backend required before enabling Recap frontend surfaces.

Actual live Alembic revision must be rechecked with authorized read-only access. Last directly
recorded revision was0021, not a claim about current state. Expected chain if unchanged:
0022 ->0023 ->0024; apply only the required suffix after backup and exact migration permission.
No downgrade as default rollback. A previous backend must not delete Events now referenced by
Recaps. Preserve DB/media, freeze writes and use a compatible forward repair if needed.

## Verification

- Backend retention/API/upload-commit/migration integration:27PASS,49.65s, disposable local DBs.
- Backend Ruff/strict mypy330 files/package:PASS. Migration history unchanged/singlehead0024.
- Frontend Recap/EN-DE/Facebook/Admin workflow:23PASS; separate actual Slider/Admin regression:30PASS.
- ESLint, TypeScript, build and final Prettier:PASS. Initial format check failed Windows line-ending/
  formatting differences; corrected and final check passed. No semantic changes to unrelated scripts.
- Demo exclusion:17 build files,10 forbidden markers absent. Dependency locks unchanged.
- Read-only loopback HTTP:200, nine published cards, one page, new isolated review DB.
- Browser inventory reports `Local browser use is disabled in Work settings`; no fresh screenshot,
  visual/mobile/axe acceptance claimed. CSS unchanged and EN/DE component interactions tested.
- Previous full936frontend/1879backend evidence belongs to Rolling10; not repeated/claimed for this
  SHA. New hosted CI must run full suites for the final candidate before Production deployment.

Review: https://127.0.0.1:5199/events/recap and /admin/events/recaps, backend loopback8045.
Synthetic credentials only in this worktree's ignored `.local/recap-review/login.json`; do not
publish them. Separate local containers `buddy-recap-rolling9-api` and
`buddy-recap-rolling9-review-db` use `buddy-recap-rolling9-review-net`. Test DB/container is separate.
Restart only these review containers if stopped; from apps/web start:

```powershell
$env:RECAP_REVIEW_PORT='5199'
$env:RECAP_REVIEW_API_PORT='8045'
node scripts/review-recaps.mjs
```

Only run Vite if5199 is free. Review EN/DE at desktop/tablet/mobile; verify9 cards/3x3 desktop,
retention warning, safe Facebook link, and optionally publish one synthetic draft to exercise the
tenth eviction/notification. Never create ten real Production Recaps for acceptance.

## Hosted CI preflight and stopped boundary

Only `.github/workflows/ci.yml` exists: unrestricted push/PR triggers, contents:read, two jobs
Frontend/Backend. No deploy/migration of hosted resources, no provider secrets, disposable runner
PostgreSQL. No auto-publication through other repo workflow. Candidate branch was absent remotely.

Exact `codex/events-recap-rolling9:false` is added in `apps/web/vercel.json`; previous two exactfalse
rules retained. No true/wildcard overlap. Main remains defaulttrue; rewrites, headers, endpoints,
environment settings and all other Vercel config unchanged. Project root apps/web / Productionmain
were directly verified earlier today, not re-observed by this task. Official behavior/true-rule
precedence rechecked: https://vercel.com/docs/project-configuration/git-configuration .

Render OFF was owner-stated and directly recorded earlier today. Fresh confirmation is pending:
no provider connector/CLI credentials, browser control disabled. No cloud settings changed.
**Do not push until current Render OFF/provider safety is confirmed.** The owner already authorizes
normal non-force candidate publication once safe; a new permission to push is not needed. Then:

1. Fetch/recheck main and remote candidate refs; if newer main, integrate and validate affected paths.
2. Require clean tree, exact SHA, suppression/project root/main behavior unchanged, Render OFF.
3. Normal exact-SHA push only to origin/codex/events-recap-rolling9; never main at this stage.
4. Find exact-SHA push workflow; verify both jobs/all steps/audits, no unexpected deployment jobs.
5. Inspect Vercel deployment records; no candidate Preview/Production, old Production unchanged.
   If inaccessible, actual enforcement UNVERIFIED. Unexpected Preview: do not open/test it; stop.
6. No backend/frontend release until CI PASS and Production gates below satisfied.

Fresh read-only GitHub main CI run41762608191 is success for6d32d1a, not for this candidate.
GitHub deployment metadata now lists Production6d32d1a (record7536457105,2026-11-04T02:44:04Z).
This corroborates a newer frontend than older685 records; it is not direct Vercel READY/domain
verification. Do not infer current Render revision or database state from it.

## Minimal Production safety / owner actions

| Gate | Status / smallest required action |
| --- | --- |
| Supabase quota | Owner Nov4 Free baseline accepted:Storage.003/1GB,egress.697/5GB,DB.09/.5GB. No repeat audit; check material change near release. |
| Complete encrypted off-project PostgreSQL backup | NOT PROVEN. Provide existing backup metadata/checksums/coverage and recovery location, or explicitly authorize one scoped Production backup export to an owner-selected encrypted destination. No export performed. |
| Critical private Storage recovery | Inventory and recoverable copies/coverage must accompany DB backup, including both Recap derivatives and pending cleanup intent. No Production download performed. |
| Restore assurance | Prior synthetic restore is useful, not Production backup proof. No actual-rehearsal waiver received. A waiver must explicitly acknowledge residual risk and never waive minimum backup protection. |
| Render capacity/upload | Owner policy:one Admin/tab, sequential uploads,<=12 photos,prefer<=1600px,quiet traffic,no retry storms; no paid upgrade. Actual p95/headroom UNVERIFIED. |
| Production performance acceptance | No write-test scope authorized. Proposal:one synthetic draft/one small image, one operator, owner-approved cleanup; sample read-only auth/Events baseline and upload period. Targets ordinaryp95<=2s/uploadp95<=3s; stop any read>5s, auth/Events failure, repeated timeout/restart/OOM. Never test overflow with live data. |
| Dev minimatch advisory | Existing GHSA-g3hv-75wg-m249 remains dev/CI availability only under fixed trusted globs, no optimizationLevel2/project-service or runtime use. Preserve narrow exception, expire2026-11-30 or earlier configuration/exposure change. No audit suppression, dependency upgrade or broad waiver. Exact-SHA hosted runtime audits still required. |
| UI review | New warning/gallery9 manual visual/mobile review outstanding; use loopback URLs. |
| Production baseline | Recheck exact Vercel/Render revisions, live Alembic, rollback refs and count<=9 before any mutation. |
| Migration / release | No export/migration/backend deployment/main push performed. Exact Production export/migration operations not yet explicitly authorized; require backup proof and operation-specific approval. |

At9x10 photos and390KiB/photo derivatives, published gallery planning average~34.28MiB
(vs38.09MiB for10):~3.81MiB less after cleanup, not a hard byte bound. Drafts/manual archives,
backups, unrelated objects and failed cleanup remain additional. Signed URLs retain existing
short<=300s/cache limitations. Upload CPU/512MB risk and deletion-call latency are not improved
or Production-verified by changing10 to9. No new infrastructure/billing/settings.

After gates: verified migration suffix -> exact backend manual deploy with AutoDeployOFF ->
health/readiness/auth/Events/Admin/Recap compatibility -> normal main integration/push -> actual
Vercel exact-SHA READY/domain check -> read-only smoke, then only approved write acceptance.
Never deploy frontend first. Main push would trigger Production and is not permitted while gates
remain missing. Preserve data; destructive recovery requires separate explicit authorization.
