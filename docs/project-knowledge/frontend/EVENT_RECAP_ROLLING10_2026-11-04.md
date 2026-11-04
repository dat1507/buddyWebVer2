# Events Recap Rolling 10 + Facebook - 2026-11-04

**Local implementation complete; new hosted CI/UI review required; Production NO-GO.**
Branch `codex/events-recap-rolling`, isolated `.local/worktrees/events-recap-rolling`.
Baseline approved/published `c74217333d4935c0e16a77735593775741486fe8`. Fresh origin/main:
`6d32d1a86e2fb87d24990355a14db91eb867a03e`, including published chatbot alignment2a4f175 and
Admin test formatting6d32d1a. Integrated locally, preserving current main functionality and
the dirty, unpublished `recap-recovery-prep` worktree. No merge commit, push, deployment,
Production database/Storage or provider setting change. Exact final local SHA is in delivery;
[complete manifest](EVENT_RECAP_ROLLING10_MANIFEST_2026-11-04.json) identifies source/paths/commits.

## Publication and permanent eviction

- Every status transition takes the same PostgreSQL transaction advisory lock **before** locking
  its Recap row. It serializes publication across requests/processes, not merely one Python worker.
- Validate localization, photo completeness and related Event visibility first. Set
  `first_published_at` only on the first successful publication; edits/unpublish/republish retain it.
  Changing an already-published Recap does not trigger overflow eviction. Stale retry409; a retry
  with current version/already-PUBLISHED is a no-op, not another eviction.
- On a transition to PUBLISHED, keep the ten greatest `(first_published_at, UUID)` pairs; remove
  every surplus published row, excluding drafts/archived/deleted rows. UUID ascending breaks ties
  for oldest selection. Event date/creation/edit time do not decide new publication retention.
  Exactly ten remain when publication would overflow. The migration fails closed if a legacy backend already has more than ten published rows; it
  never silently destroys content during schema upgrade. Review/reconcile such legacy data before
  upgrading, and freeze old-backend publication during rollout. Normal eleventh publication under
  this backend requires no manual deletion. The service also repairs an oversized set caused by
  out-of-contract direct writes on its next successful new publication.
- Publication, audit, durable media-cleanup jobs and hard deletion of evicted Recap/photo/image
  metadata are in one transaction. Failed validation/audit/commit does not delete old files.
  Thumbnail cyclic FK is cleared, photo/image rows cascade; the original linked Event is untouched.
  No automatic Archive or extra confirmation/manual delete step. Drafts are not retention victims.
- Original-clock consequence: republishing an old unpublished memory can evict itself if ten
  newer memories already exist. The UI handles this by returning to the list with the eviction
  notice, rather than opening an editor for a nonexistent Recap.
- Public list/detail/new media signing exclude deleted rows immediately after commit. Previously
  issued signed URLs retain their existing <=300s lifetime/cache limitation; no instant CDN/browser
  cache revocation is promised. Physical object deletion normally makes uncached reads unavailable.

## Durable physical cleanup

New private `recap_media_cleanup` rows contain only evicted Recap UUID and server-owned event-media
object keys, not deleted title/editorial/alt/caption content. They have no FK to the deleted Recap.
Both display and thumbnail variants, including any retained deleted-photo cleanup refs, are queued
before metadata deletion. Generic Storage reference discovery sees queued keys and protects them
from premature orphan reconciliation.

After publication commits, attempt network deletions with no long database transaction held.
Only event-media keys from evicted RecapImage rows are candidates; never profile/slider buckets.
An unexpected live EventMedia/RecapImage owner fails closed and leaves work pending. Each successful
delete removes its job; partial failure/process interruption retains remaining jobs. A later404
means a prior delete succeeded and its job can finish. Retries are idempotent and cannot re-evict
another Recap or delete its Event. No new worker/service/bucket is introduced.

Response includes evicted identities/titles and truthful `cleanup_pending`. Admin notification names
the old Recap; if Storage is unavailable it explicitly reports pending cleanup, not complete physical
success. Existing Admin pending-cleanup list/retry mechanism now includes permanently deleted Recap
IDs. Retry works without a surviving Recap row; repeated completed retries return no pending work.
Normal overflow needs no extra action. Storage outages may require the existing cleanup retry;
this release does not add an automatic background retry scheduler. Permanently deleted content is
not retained for browsing in the cleanup queue.

## Frontend and preserved behavior

Existing Event Slider / Events Recap tabs, editor/upload/captions/order/thumbnail/draft/preview/
publish/unpublish/delete controls remain. A compact permanent-retention warning appears on list
and editor; eviction is announced through a status region with EN/DE titles and no added dialog.
Manual Archive remains an existing explicit action; automatic overflow never calls it.

Public page keeps its mosaic, cream/orange/green layout, stories, gallery/lightbox, shared typography
and controls. Public API page size is10, so ten recent memories fit one page; Admin remains9/page
for unlimited drafts. Year filtering remains. The responsive green section “Looking for More
Memories?” links to `https://www.facebook.com/VGUBuddyProgram` through “Explore More on Facebook”,
EN/DE, target_blank + noopener/noreferrer. No Facebook API, scraping or media synchronization;
Facebook does not automatically preserve the deleted BuddyWeb content.

Current-main chatbot source/landing stylesheet and existing Events/Slider/Merchandise/locks remain
byte-identical to main (35 checked shared source/lock paths). Admin Events source still differs
from main only by the previously approved tab import/render. Its reconciled test retained the
tested async table-scoped German selectors and main's formatting. Documentation reconciliation retained
both dated histories. No unpublished unrelated chatbot branch was imported.

## Verification and exact limits

- Focused initial backend retention/migrations/commit safety22PASS; later full backend
  **1,879 PASS /37 existing opt-in SKIP /one existing deprecation warning**, no failures.
- Final affected subset rerun after a small404-cleanup hardening/new regression and self-contained
  fresh-CI role fixture: **27 PASS**. After the final legacy-overflow migration guard,
  the upgrade/backfill guard and existing live API subset passed **3 tests**; focused typing and
  package checks also passed. The already-passing full backend was not
  unnecessarily repeated; final lint/strict mypy330 and package gates rerun. No new skipped tests
  or timeout increases. Both Recap live suites run against disposable local PostgreSQL in CI.
- Full frontend **936 PASS /96 files /zero skip**; focused gallery/Facebook/notice/Admin/Slider33PASS
  plus actual Admin EN/DE workflow2PASS. Count change vs925: three current-main chatbot tests plus
  eight new Facebook/feedback/workflow cases. Public pagination regression now asserts ten cards.
- Prettier, ESLint, TypeScript, production build and backend Ruff/mypy/package/headPASS. Single
  Alembic head0024. Demo exclusion17 build files/10 forbidden markersPASS. Dependency locks unchanged;
  reuse previous runtime audits; the existing dev minimatch advisory remains an owner disposition.
- Boundary0/1/9/10/11, original-time/UUID tie, editing/retries, invalid publication, atomic rollback,
  concurrent different publications, partial/failed cleanup/durable jobs/reference discovery,
  deletion-ack loss404, original Event protection and public404/new signing denial covered.
- Real loopback HTTP + PostgreSQL + Pillow + local Supabase Storage smoke7PASS: initial ten,
  upload/create/publish11th, automatic eviction, cleanup complete, public/media404, single-page ten,
  repeat publication causes no additional eviction. Synthetic review data only.
- Browser control reports **disabled in Work settings**. No fresh visual/responsive/axe claim is
  made. Existing responsive grid/CMS/shared styles retained; new section uses fluid padding/text
  wrapping/44px link. Automated EN/DE interactions pass, but changed UI visual review remains open.

Initial new-test failure was an incomplete synthetic photo fixture (one variant); corrected to two
variants. Final hosted-CI fixture explicitly creates its anon NOLOGIN role locally before asserting
grants. No Production or approved review data used for test setup. Logs/env/login/artifacts are in
ignored `.local/rolling` and `.local/recap-review`; credentials are never committed or printed.

## Migration, cost and recovery impact

New **0024_recap_retention** follows0023; sequence0021 ->0022 ->0023 ->0024 remains linear and tested
fresh/from0021, plus explicit0023 upgrade/backfill. Adds original publication timestamp/index and
private RLS/runtime-only cleanup table. Earliest audit record with statusPUBLISHED recovers legacy
original time; creation timestamp is an explicit fallback where no publication audit exists. This
fallback cannot reconstruct unavailable historical facts. No metadata/media deletion in migration; explicit legacy-overflow rejection preserves all old
rows and schema on failed upgrade, tested along with normal backfill.

Backups now need `first_published_at` and cleanup jobs as well as Recap/Photo/Image metadata and
both derivatives. Earlier27-table synthetic restore evidence does not certify this new28-table
schema. Actual full Production backup/restore remainsBLOCKED; Rolling10 does not waive it or accept
reduced assurance. Consistent recovery must reconcile queued deletion intent before running any
cleanup; an older snapshot may contain memories intentionally evicted later. Restore/retention/RPO
and media reconciliation require owner incident decisions. Never default to destructive downgrade.

At ten photos/Recap and350+40KiB derivatives/photo, ten published memories need~38.09MiB. At twelve
photos each,~45.70MiB. This is a planning average, not a guaranteed upper byte bound. Compared with
100 retained published memories at~380.86MiB, rolling ten avoids~342.77MiB once physical cleanup
finishes. Drafts, manual archives, pending cleanup, backups and unrelated media remain additional
and potentially unbounded; outage/backlog prevents immediate savings. Owner Supabase initial
Storage quota evidence remains relevant, but monitor all-project Storage/egress near release.

No additional paid infrastructure. Decoder/file/photo bounds unchanged; earlier RenderFree0.1CPU/
512MB contention and timeout risks remain. Eviction adds up to24 Storage DELETE calls for one
12-photo memory; the response may exceed client deadline during outages, while committed deletion
intent remains durable. Retrying current published state must not trigger another eviction; inspect
saved state and pending cleanup. Keep one operator/tab, serial smaller-image batches, quiet periods
and previously proposed stop thresholds. Actual headroom/performance acceptance staysUNVERIFIED.

## Local review / restart

Running isolated review: **https://127.0.0.1:5198/events/recap** and
**https://127.0.0.1:5198/admin/events/recaps**, backend loopback8044. Earlier5197/8043 review and all
original worktrees preserved. The smoke has already exercised an11th publication; gallery now has
ten, with a “Rolling 11 local acceptance” entry. Admin uses only the synthetic credentials in this
worktree's ignored `.local/recap-review/login.json`; no credentials or real account use in Git/chat.

PowerShell from this worktree, existing local Supabase Storage must be running:

```powershell
docker start buddy-recap-rolling-db
docker start buddy-recap-rolling-api
Set-Location .\apps\web
$env:RECAP_REVIEW_PORT = '5198'
$env:RECAP_REVIEW_API_PORT = '8044'
node .\scripts\review-recaps.mjs
```

Run last command only if5198 is free. Review API validates loopback origin/database and fixture
seeding does not repeat when any Recap exists, including after the original welcome is evicted.
To review overflow, create/save a draft, upload one image and publish while ten are published;
observe named eviction, ten-card gallery, old detail404. Try EN/DE at desktop/tablet/mobile and
the Facebook link. No new image assets or Windows trust changes introduced.

## Readiness / next release steps

| Gate | Status |
| --- | --- |
| Local Rolling10 correctness/API/cleanup |PASS|
| Existing accepted UI functionality |Preserved; changed warning/CTA/notification need local visual review|
| New exact-SHA hostedCI |REQUIRED; previousc742173 run does not cover this candidate|
| CI-only Vercel safety |Exactfalse for both RC and new rolling branch; main remains eligible; no push now|
| Supabase initial Storage forecast |Owner baselinePASS; drafts/backlog/traffic still monitored|
| Actual full backup/recovery |BLOCKED; no waiver|
| Render capacity/Production upload+eviction acceptance |UNVERIFIED|
| Dev advisory disposition |OWNER ACTION REQUIRED|
| Production readiness |NO-GO|

Next: local changed-UI review; separately authorize exact new-SHA CI-only publication after trigger
recheck, run hostedCI; close recovery/capacity/advisory gates. Separately approve0024-inclusive
migration before new backend. Freeze old-backend Admin Recap status writes during transition:
old code can bypass Rolling10 and cannot read the new cleanup queue. Deploy backend with Render
Auto-DeployOFF; verify existing Events/auth and retention/cleanup before updating main/frontend.
Vercel auto-deploys main; do not merge frontend first. Recheck newer main and exact-SHA eligibility.
After permanent eviction, frontend rollback cannot restore content; preserve DB/media and use a
Recap-aware forward repair/write freeze. Recovery of evicted memories needs an authorized complete
backup restore/data-reconciliation decision. No release operation is authorized by this local task.
