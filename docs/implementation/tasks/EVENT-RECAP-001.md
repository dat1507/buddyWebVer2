# EVENT-RECAP-001 — Events Recap

Assigned by owner 2026-11-03. IN PROGRESS. Local implementation, verification and commits only.
Baseline `c64fe73e17fedd8d92046bbc7beeedd0a22e2646`; branch `codex/events-recap`.
The owner's full Events Recap request supersedes the old unassigned recap contracts for this scope.

## Sequential checkpoints

0. Architecture/cost audit: existing React/Vercel, FastAPI/Render, private PostgreSQL and event-media
   Storage. No new dependency, bucket, service or subscription. Current account usage/quotas UNKNOWN.
1. Public gallery and reusable detail/lightbox, EN/DE, 9-card pagination, isolated test fixtures.
2. Dedicated recap, photo and derivative metadata; private existing image pipeline; admin/CSRF/audit/
   version checks; publication independent of Event; restricted related Events never projected publicly.
   Fix existing Alembic version capacity without rewriting published revisions; disposable migration tests.
3. Preserve Event CRUD; two route-backed Events tabs; recap editor, sequential multi-upload, retry,
   captions/alt/order/thumbnail, draft/preview/publication/archive/deletion.
4. Isolated real local API/database/storage integration and responsive browser review.
5. Focused security/regression/static/build checks, measured derivatives, forecast, screenshots/restart.

## Architecture and cost decisions

One Recap may reference an Event; never duplicate or mutate the Event. Photos own exactly two WebP
derivatives (480px and 1600px bounding boxes, no upscale, metadata removed); original retention OFF.
Each derivative follows the existing bucket/object_key ownership discovery convention so orphan
reconciliation protects it. Use existing event-media bucket and short signed delivery after authorization.
One bounded processing job per API process, one upload per browser, max 12 photos and 5 MiB/file.
Uploads use stable client UUID plus content fingerprint for safe retry. Soft-delete before object cleanup;
failed cleanup stays retryable. No paid transformations or processing on public reads.

Added infrastructure cost target $0; incremental storage/egress/CPU still consume existing quotas.
Provider subscription, usage, remaining capacity, overage settings and actual monthly traffic UNVERIFIED.
No Production data, secrets, migrations, provider settings, push, merge or deploy authorized.

## Focused source and verification scope

`apps/web/src/features/recaps/`, new public/admin recap pages, App routing, Events tabs, EN/DE locales,
existing Event/navigation regression tests; `apps/api/app/{models,schemas,services,api}/recap*`,
existing image_storage/multipart, main router, model exports, Alembic environment and new migration.
Focused tests cover publication/related-event visibility, IDOR, auth/CSRF, stale versions, retry,
12-photo cap, metadata stripping, cleanup failure/recovery, deterministic pagination and migration paths.
Final evidence and local review instructions will be recorded here or in one linked recap report.
