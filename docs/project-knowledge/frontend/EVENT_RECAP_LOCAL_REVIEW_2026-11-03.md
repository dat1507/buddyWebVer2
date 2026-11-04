# Events Recap — local implementation and review

2026-11-03 (Asia/Saigon). Task [EVENT-RECAP-001](../../implementation/tasks/EVENT-RECAP-001.md).
Local feature branch `codex/events-recap`, based on approved Event/Merchandise frontend
`c64fe73e17fedd8d92046bbc7beeedd0a22e2646`. Primary dirty work and unpublished history preserved.
No push, merge, deployment, Production data access, Production migration or cloud configuration change.
Render Auto-Deploy was not inspected or changed; the owner's OFF instruction remains in force.

## Delivered behavior

- Public `/events/recap`: localized cream/green mosaic, distinct published recaps, year filter,
  deterministic latest-first ordering, nine cards per page, honest empty/error states.
- `/events/recap/:recapId`: ordered photo highlights, full thumbnail gallery, captions, optional
  date/story, keyboard lightbox with focus isolation/restoration, count, Escape and reduced motion.
- Existing Admin Events management stays at `/admin/events`. Exactly two navigation links select
  Event Slider and Events Recap, preserving existing Event URLs and their independent launch gate.
- Recap CMS supports independent draft/publication/archive, standalone or related Event, EN/DE
  content, optional editorial text, multi-file selection/drop, serial upload, per-file indeterminate
  progress/errors/retry, captions/alt, move-up/down ordering, thumbnail choice, saved preview and
  confirmed deletion. Event date prefilling uses the related Event's timezone.
- Public and Admin recap routes load as separate bundles. No demo data is imported into application
  runtime; review fixtures live in an explicitly invoked local-only script and disposable database.

## Persistence, security and image lifecycle

`recaps`, `recap_photos`, `recap_images` live in `app_private`, with RLS and backend-only grants.
The Recap is independent of Event publication. Anonymous list/detail/media authorization also
requires any related Event to be published, PUBLIC and non-deleted. MEMBERS Events are excluded
even though older Event projection conventions differ. Active related recaps guard Event deletion;
deleted recap tombstones detach safely so the original Event is not permanently blocked.

All Admin mutations use current persisted ADMIN authorization, session CSRF, audit records and
locked optimistic versions. Strict input DTOs bound text and gallery size. Public DTOs exclude
object keys, upload IDs, fingerprints and actor identities; prose renders as text. A composite
thumbnail FK and service checks enforce ownership. Stable upload UUID + source fingerprint makes
lost-response retries idempotent. Deleted upload IDs cannot resurrect removed photos.

Uploads reuse existing filename/MIME/signature/full-decode/dimension/pixel/animation validation and
Pillow 13.0.0. Inputs remain at most 5 MiB and 4096×4096. Validation applies orientation before
creating metadata-free WebP derivatives, bounded at 1600px and 480px on the longest edge, without
upscaling. Originals are deliberately not retained: the agreed gallery/lightbox needs display
quality, not archival originals. A gallery photo also supplies its thumbnail; there is no extra cover.

One decoder runs per API process. The gate is acquired before reading the bounded multipart body;
busy requests return 429 for safe retry. Cancellation keeps the gate until the Pillow thread finishes.
CPU work runs off the event loop and only at upload time. The intermediate validation image is
bounded before expensive clean copies. Each derivative follows the existing bucket/object_key
ownership convention, so generic orphan reconciliation protects both variants. Storage uses the
existing private `event-media` bucket; no new bucket, transformation provider or service is created.

Media capabilities are authorized on demand, last at most 300 seconds, and refresh after 240 seconds
in the client cache. Thumbnail signing requests are limited to three simultaneously. Images are
lazy, dimensioned and only request the display variant in the lightbox. A failed image refreshes
once; persistent outages show safe fallback text, with explicit retry in the lightbox. Previously
issued signed capabilities can remain usable until expiry after unpublication; this follows the
existing private-media design rather than promising instant revocation.

Deletion hides content transactionally before Storage cleanup. Failed derivative references remain
durable, appear in Admin cleanup warnings even for deleted recaps, and can be retried. Uncommitted
upload failures are compensated; the existing age-gated orphan mechanism covers interrupted cleanup.

## Migrations

New revision `0023_recaps` follows unchanged `0022_public_event_visibility_default` and creates only
the recap tables, constraints, indexes and private grants/policies. The Alembic environment now
creates a 128-character version column and widens an existing column before migration execution.
This fixes the known 36-character revision / default VARCHAR(32) fresh-install defect without
renaming any published revision. Fresh installation, representative 0021 + VARCHAR(32) upgrade,
offline SQL generation, single head and runtime grants were verified locally. No Production
migration was run. A release must apply the backend/schema before enabling the new frontend.

## Verification

| Gate                             | Evidence                                                                                                                                                                                            |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend full suite              | 90 files / 838 tests PASS; final timezone helper adds two focused cases                                                                                                                             |
| Shared image/security regression | 92 PASS after intermediate-memory and cancellation fixes                                                                                                                                            |
| Event/Recap backend              | Focused Event/media/API gate originally 117 PASS; expanded run found one offline-SQL formatting defect, fixed; all 12 affected migration/live API tests then PASS; final Event/deletion API 33 PASS |
| Backend typing                   | 140 source files PASS after final follow-up                                                                                                                                                         |
| Static/build                     | Frontend ESLint, TypeScript, production build and backend Ruff PASS                                                                                                                                 |
| Real browser CRUD                | 29 PASS: real Admin login, tabs, draft, two-file upload, metadata/order/thumbnail refresh, preview, publish/unpublish/archive/delete, lightbox, 18 EN/DE width cases                                |
| Browser failure paths            | Four PASS: committed upload with lost response retries without duplicates; thumbnail fallback notification; expired URL recovery; Storage outage fallback                                           |
| Accessibility                    | 18 gallery/detail/editor cases, EN/DE × 1440/768/390, zero WCAG A/AA violations after fixing loading semantics                                                                                      |
| Runtime                          | Zero uncaught JavaScript errors in the complete workflow                                                                                                                                            |

The build retains the existing >500 kB main-bundle warning. New recap page/editor code and CSS are
split; no unrelated global bundle rewrite was attempted. Focused tests cover auth/CSRF, IDOR,
publication/restricted Events, stale versions, duplicate retries, image safety, cleanup failures,
thumbnail fallback, 12-image cap, no lifetime record cap and stable pagination. Existing Matching,
auth, Landing, Merchandise and dashboard tests are included in the full frontend suite.

Local evidence is under `.local/recap-review/` (ignored): `browser-results.json`, `edge-cases.json`,
`accessibility.json`, `image-measurements.json`, final screenshots and helper runners. These contain
no Storage capabilities or credentials. Ignored `login.json` and `*.env` are private setup inputs,
not evidence, and are not committed. Provider transport security is regression-tested, and the browser
also exercised actual existing local Supabase Storage, not an in-memory replacement.

## Measured resources and cost assumptions

Five already-optimized repository WebP images, local Python 3.12 / Pillow 13 container:

| Metric                   | Measured mean |
| ------------------------ | ------------: |
| Source input             | 178,068 bytes |
| 1600px display           | 159,374 bytes |
| 480px thumbnail          |  24,417 bytes |
| Two retained derivatives | 183,791 bytes |
| Processing per photo     |  0.73 seconds |

The sources are already compressed: two derivatives average about 3.2% more bytes than those inputs.
This is not a claim that every upload shrinks. Thumbnails average about 85% fewer bytes than display
images, reducing card/mosaic traffic. Source originals are not stored in addition to these variants.
A uniform synthetic 4096×4096 JPEG took 0.85 seconds; peak process RSS was 247.3 MiB, down from
387.5 MiB before reducing intermediate copies. This is a local probe, not a worst-entropy benchmark
or proof of available Render memory. Production baseline memory and concurrent non-image load are
UNVERIFIED. Ten photos represent about 7.3 local CPU seconds spread over ten serial upload requests.

Planning budget: **10 photos/Recap, 350 KiB display + 40 KiB thumbnail per photo**. This is deliberately
above the measured averages. Metadata/index size, cleanup backlog and provider accounting require
additional headroom. Storage below is MiB; no original retention is included.

| Recaps | Photos | Originals retained | Display | Thumbnails | Total budget | Same count at measured mean |
| -----: | -----: | -----------------: | ------: | ---------: | -----------: | --------------------------: |
|     10 |    100 |                  0 |   34.18 |       3.91 |        38.09 |                       17.53 |
|     50 |    500 |                  0 |  170.90 |      19.53 |       190.43 |                       87.64 |
|    100 |  1,000 |                  0 |  341.80 |      39.06 |       380.86 |                      175.28 |
|    200 |  2,000 |                  0 |  683.59 |      78.13 |       761.72 |                      350.55 |

Upload traffic is separate: up to 5 MiB/photo reaches the backend, but is not retained. Each photo
creates one API upload and two Storage PUTs; later deletion needs two Storage DELETEs. At the sample
mean, 10/50/100/200 Recaps cost roughly 73/365/730/1,460 local processing seconds in total.

Monthly traffic assumptions, intentionally uncached upper estimates: each list visit loads up to
14 thumbnails (nine cards + five mosaic; actual overlap is deduplicated); each detail visit loads
ten thumbnails and two display images. Thus list ≈560 KiB, detail ≈1,100 KiB. API estimates include
one content read and one signed-URL read per viewed variant. Long open pages add URL renewal calls
every four minutes; browser/provider cache hits can reduce image transfers.

| Traffic | List visits | Detail visits | Estimated media egress (GiB) | Additional API requests |
| ------- | ----------: | ------------: | ---------------------------: | ----------------------: |
| Low     |       1,000 |           100 |                         0.64 |                  16,300 |
| Medium  |      10,000 |         1,000 |                         6.39 |                 163,000 |
| High    |     100,000 |        10,000 |                        63.90 |               1,630,000 |

These are assumptions, not observed traffic. Media egress uses existing Storage; API JSON/signing
also consume backend requests/egress. No paid image transformation is invoked. Added infrastructure
provisioned: **none**. Incremental cloud bill target: **$0 only while existing allowances suffice**.

## Provider quota status and owner checks

Connected Supabase organization metadata on 2026-11-03 directly confirms `plan=free`, `tier=tier_free`.
No account Storage/egress usage endpoint is exposed by the installed connector. Current used bytes,
remaining capacity, cached/uncached bandwidth, request allowances and billing controls are UNVERIFIED.
Render Free is the repository's last recorded service selection, not a fresh dashboard observation.
Current Render/Vercel subscription, included capacity, consumption and overage settings are UNVERIFIED.
Vercel team inventory returned no teams and supplied no usable billing/usage data. No quota is assumed
to be unlimited and no plan, overage, monitoring resource or provider setting was changed.

Before any separately authorized release, the owner should record:

1. Supabase Dashboard → owning organization → Billing/Subscription and Usage, select the current
   billing period and correct project. Record Storage bytes/quota, total/cached/uncached egress,
   database size, applicable request/transformation limits and existing spend controls. Compare the
   forecast with **remaining** quota after other projects/workloads. See official
   [Storage size](https://supabase.com/docs/guides/platform/manage-your-usage/storage-size) and
   [egress](https://supabase.com/docs/guides/platform/manage-your-usage/egress) accounting.
2. Render Dashboard → existing API service → Settings/Instance Type and Metrics: record current tier,
   baseline/peak memory and CPU; workspace Billing/usage for hours and outbound bandwidth. Preserve
   Auto-Deploy OFF. Use the existing [Free-service usage guidance](https://render.com/docs/free).
3. Vercel Dashboard → existing project/account → Settings/Billing and Usage: record current tier,
   transfer/request/build allowances and month-to-date consumption. No new project is needed.

Manual warning thresholds: at **70%** used, compare projected month-end usage; at **85%**, review new
upload batches and cleanup backlog before proceeding; at **95%**, stop additional resource-consuming
operations until capacity is confirmed. Apply separately to Storage, egress and backend limits, with
existing workload included. Use existing dashboard notifications where already configured; otherwise
review manually after each content batch and weekly, increasing to daily above 85%. No new external
monitor, subscription upgrade or paid-overage action is automated. If remaining quota is insufficient,
stop that release/upload operation and obtain an owner decision; an accurate paid upgrade estimate
requires the missing account baseline and is not invented here.

## Local review and PowerShell restart

Worktree: `C:\Users\phuoc\Downloads\buddyWebVer2\.local\worktrees\events-recap`.
The running review uses dedicated `buddy-recap-db` and `buddy-recap-review-api`, existing local
Supabase Storage/Kong on port 54321, the existing local TLS certificate, and Vite on 5197. No trust
store or existing provider configuration changed. The API binds only loopback host port 8043.

- [Gallery](https://127.0.0.1:5197/events/recap)
- [Persistent three-photo detail](https://127.0.0.1:5197/events/recap/6eab5d5f-3ed3-4c71-bd8a-81fa3ba8e691)
- [Admin Event Slider](https://127.0.0.1:5197/admin/events)
- [Admin Recaps](https://127.0.0.1:5197/admin/events/recaps)
- [New Recap](https://127.0.0.1:5197/admin/events/recaps/new)

For Admin, use the local-only synthetic login stored privately in `.local/recap-review/login.json`.
It is separate from real accounts. The local harness never sends email or accesses Production data.
If the local servers have stopped, run in PowerShell (the existing local Supabase containers must
also be running; do not repoint this harness at a cloud project):

```powershell
Set-Location 'C:\Users\phuoc\Downloads\buddyWebVer2\.local\worktrees\events-recap'
docker start buddy-recap-db
docker start buddy-recap-review-api
Set-Location .\apps\web
node .\scripts\review-recaps.mjs
```

Only run the last command when port 5197 is free; the current hidden background process already
serves it. The script loads existing TLS files relative to this worktree location; another checkout
can supply `LOCAL_TLS_CERT_FILE` and `LOCAL_TLS_KEY_FILE` explicitly. The retained container mounts
this exact worktree and its ignored environment file. Recreating the local database/setup requires
fresh synthetic credentials, the cached Python 3.12/Pillow 13 image, migrations and the existing
local Storage credential; none is committed or embedded in command arguments.

Screenshots (local artifacts, intentionally outside Git):

- [Gallery 1440px](../../../.local/recap-review/gallery-review-1440.png)
- [Details 1440px](../../../.local/recap-review/details-review-1440.png)
- [Gallery 390px](../../../.local/recap-review/gallery-review-390.png)
- [Admin sub-tabs](../../../.local/recap-review/admin-subtabs.png)
- [Multi-upload and retry](../../../.local/recap-review/admin-upload-retry.png)

## Modified source areas and remaining limits

Backend: new recap model/schema/service/API/image processor/Event relation adapter; model exports,
main router, prepared-image storage method, opt-in output sizing; Alembic environment/revision;
image/live migration/security tests. Frontend: route boundaries; public gallery/detail/story/image
components; shared Events tabs and Admin CMS; EN/DE resources; existing Events list gets only the
tab navigation; focused recap and updated placeholder/navigation tests. Review launchers are
`apps/api/scripts/recap_review.py` and `apps/web/scripts/review-recaps.mjs`.

Known limits: move-up/down controls are the accessible ordering mechanism; pointer drag reordering
is deferred, while drag/drop upload is supported. Upload progress is indeterminate while server
processing runs, with per-file queued/success/failure states. Draft preview shows saved content.
Source archival download is outside this scope because originals are not retained. Account quotas,
real traffic and Render load/capacity require owner checks before release. Automated accessibility
checks and keyboard smoke do not replace manual assistive-technology testing. No release is authorized.

<details>
<summary>Exact changed paths</summary>

```text
SESSION_HANDOFF.md
apps/api/alembic/env.py
apps/api/alembic/versions/0023_recaps.py
apps/api/app/api/admin_events.py
apps/api/app/api/recaps.py
apps/api/app/main.py
apps/api/app/models/__init__.py
apps/api/app/models/recap.py
apps/api/app/schemas/recap.py
apps/api/app/services/image_storage.py
apps/api/app/services/recap_images.py
apps/api/app/services/recap_relations.py
apps/api/app/services/recaps.py
apps/api/scripts/recap_review.py
apps/api/tests/test_migrations.py
apps/api/tests/test_recap_images.py
apps/api/tests/test_recaps_live.py
apps/web/scripts/review-recaps.mjs
apps/web/src/App.tsx
apps/web/src/features/recaps/admin-events-tabs.tsx
apps/web/src/features/recaps/recap-photo.tsx
apps/web/src/features/recaps/recap-story.test.tsx
apps/web/src/features/recaps/recap-story.tsx
apps/web/src/features/recaps/recaps.css
apps/web/src/features/recaps/recaps.test.ts
apps/web/src/features/recaps/recaps.ts
apps/web/src/locales/de/common.json
apps/web/src/locales/en/common.json
apps/web/src/pages/admin/admin-events-page.tsx
apps/web/src/pages/admin/admin-recap-pages.tsx
apps/web/src/pages/public/community-coming-soon-page.test.tsx
apps/web/src/pages/public/recap-pages.test.tsx
apps/web/src/pages/public/recap-pages.tsx
docs/implementation/production-status.md
docs/implementation/task-index.md
docs/implementation/tasks/EVENT-RECAP-001.md
docs/implementation/validation.md
docs/project-knowledge/backend/README.md
docs/project-knowledge/database/README.md
docs/project-knowledge/frontend/EVENT_RECAP_LOCAL_REVIEW_2026-11-03.md
docs/project-knowledge/frontend/README.md
implementation-plan.md
```

</details>
