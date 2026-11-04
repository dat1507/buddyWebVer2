# Events Recap hosted CI safety preflight - 2026-11-04

**Publication BLOCKED. Production NO-GO.** Input cdfc863503371ffef823f0a825162e7a1581c540 was
clean and includes fresh origin/main6851725362184af7c85828602b6c881f64374b60. All recorded
application/CI hashes still match it. This preflight adds documentation/evidence only; no runtime,
workflow, dependency or provider configuration changed. Final HEAD is a documentation successor,
whose exact SHA is in the delivery message. No push/deploy/migration occurred.

## Hosted trigger assessment

GitHub: only `.github/workflows/ci.yml`; unrestricted push/pull_request triggers, contents:read.
Jobs install locked dependencies, test/lint/type/build/audit and validate Compose. Alembic upgrade
tests use an explicitly disposable runner-local PostgreSQL service. No deploy, Production migration,
remote credential reference, workflow dispatch, reusable workflow or backend resource creation.
Frontend build is tsc/Vite; no application API calls or deploy lifecycle scripts. Repository workflow
is safe for CI-only publication. Account-level webhooks/other GitHub Apps are outside this inventory;
do not claim a comprehensive account audit.

Fresh read-only Vercel dashboard checks:

- Production Branch Tracking: **main**; custom Production domains auto-assigned there.
- Preview Branch Tracking: enabled, **all unassigned branches**, **no domains attached**.
- No custom environments. Build root **apps/web**, Vite, no build/install overrides, Node24;
  Ignored Build Step Automatic. Unaffected-root skipping enabled, which does not establish a safe
  first push for a new branch containing changed application files. No deployment checks configured.
- Connector environment metadata confirms separate encrypted `VITE_API_URL` entries for Production
  and Preview. Different scope entries do not prove different target values. Production-only keys:
  VITE_ADMIN_EVENTS_ENABLED, VITE_PUBLIC_EVENTS_ENABLED, VITE_CHATBOT_ENABLED. Shared key:
  VITE_EVENT_SLIDER_USE_MOCKS. No values were decrypted or recorded.
- Preview API reveal requires owner verification. Cancelled without sending a code. Target remains
  UNKNOWN, not assumed staging. Shared team variables were not exhaustively verified.
- Render directly reconfirmed main/c0687ba, Auto-Deploy **OFF**, Free **0.1 CPU /512 MB**.
  No provider settings were edited. Available metrics do not prove actual headroom.

Expected push now: GitHub CI runs; Vercel may build/deploy Preview automatically, not Production;
Render has no authorized automatic deploy path. CI success does not itself promote Vercel Preview.
Unknown Preview backend makes this path BLOCKED. Public Recap has no dedicated feature flag and
activates with this frontend. Missing Preview Events/Admin flags default OFF, but **do not disable
public Recap or session bootstrap**. Production bundles exclude Slider mocks because DEV=false.

API client uses configured API base with credentials:include. Session bootstrap obtains CSRF,
reads /auth/me and may POST /auth/refresh after401. Thus merely opening Preview is not guaranteed
read-only against its API. CORS, cookie behavior and ADMIN checks are not verified isolation.
Frontend has no direct database credentials or Supabase service secret; database/Storage access is
mediated by whichever backend VITE_API_URL selects. That backend may issue private Storage URLs.
Neither database nor Storage separation can be inferred from Vercel environment names.

## Smallest safe CI-only remediation (prepared, NOT applied)

[Reviewable patch](../../operations/events-recap-ci-only-proposal.patch) adds only this branch rule
to apps/web/vercel.json; existing rewrites/headers remain semantically unchanged:

```json
"git": { "deploymentEnabled": { "codex/events-recap-rc": false } }
```

`git apply --check --ignore-space-change` passes (Windows CRLF context). Official [Vercel Git configuration](https://vercel.com/docs/project-configuration/git-configuration)
documents that false suppresses Git deployment for that branch; unspecified branches default true.
This is a concrete CI-only path with no reachable new Preview, no new service and no dashboard
mutation. It changes repository Vercel configuration, so it remains unapplied under the owner's
explicit no-settings-change restriction. Authorize this specific patch, or owner-disable Preview
tracking for the publication window and provide evidence. Do not rely on a commit-message skip or
Ignored Build Step to establish isolation.

After separately authorized suppression: apply/review patch, validate JSON/config-only diff,
commit locally, record NEW SHA and invalidate prior exact-SHA hosted assumptions. Reconfirm Render
OFF/branchmain and Vercel Production branchmain. Request specific push approval for the new SHA.
Only then use `git push origin <NEW_SHA>:refs/heads/codex/events-recap-rc` (no force/main merge).
Confirm Actions runs on that SHA and no new Vercel deployment/Production alias/backend/migration.
If a deployment unexpectedly appears, stop hosted interaction and investigate; do not auto-rollback
or mutate provider settings. Preview acceptance remains separate until target/database/Storage
isolation is proven. Existing cdfc863 cannot gain this committed suppression without a new SHA.

Alternative owner action for actual Preview: privately verify Preview VITE_API_URL and backend's
database/Storage targets are isolated; confirm trusted origins and test-only accounts; provide only
a redacted isolation attestation, never credentials or private URLs. Current local test backend is
not reachable from Vercel and no hosted backend/tunnel was created. If no existing isolated backend
is available, prefer the CI-only path rather than provisioning infrastructure.

## Focused performance investigation

[Sanitized measurements](EVENT_RECAP_HOSTED_PREFLIGHT_EVIDENCE_2026-11-04.json) record distributions
for liveness, persisted auth, Admin Events, public Events and Slider. Three local Docker runs:
512 MiB with0.1 CPU/4096px, 1 CPU/4096px control, and0.1 CPU/1600px mitigation. ASGI, real disposable
PostgreSQL, in-memory Storage, default-OFF chatbot; existing live acceptance fixture supplies real
auth/CSRF and a Recap upload. Hook stops after the focused comparison, not a full-suite rerun.
Cold then warm zero-upload phases, one decoder plus reads, then one decoder plus eight competing
authenticated upload requests. Six observations per read endpoint per phase; eight busy responses.
Five reads run concurrently per round. With n=6, empirical p95 equals maximum; this is not a stable
traffic/SLO estimate. Phases are ordered; host/cache variance and real network/Storage are not modeled.

0.1 CPU/4096px, **p50 / empirical p95 milliseconds**:

| Endpoint | Warm zero uploads | One decoder | Decoder +8 upload requests |
| --- | ---: | ---: | ---: |
| Liveness | 50 /96 | 102 /285 | 101 /202 |
| Auth /me | 404 /499 | 1052 /1397 | 1349 /7494 |
| Admin Events | 395 /492 | 946 /1101 | 1149 /2505 |
| Public Events | 391 /406 | 850 /1301 | 1099 /6098 |
| Slider | 190 /295 | 497 /591 | 848 /1902 |

All reads returned200. All eight competing uploads returned429, but took p50 8,896 /max8,985ms.
They still perform session/role dependency work before reaching the route's busy check. They did
not queue eight decoders. Existing CMS uses a serial await-per-file loop; this worst case models
multiple tabs/admins/retries, not one normal upload batch.

At0.1 CPU, cold no-upload auth/Admin peaks4.50/4.71s; warm baseline whole phase2.824s, one-decode
phase13.794s, multiple-request phase15.700s. CPU usage one-decode1.376s over13.794s wall with138
throttled periods, consistent with the0.1 quota. Maximum event-loop scheduling lag: warm184ms,
one954ms, multiple3583ms; cold2492ms even with no upload. Cgroup throttled time can sum across
threads and must not be interpreted as wall time or CPU usage.

At1 CPU, cold auth/Admin peaks456/480ms; warm auth p50/p95 **38.9/43.0ms**, Admin33.2/38.0ms. One-decode auth61.3/87.3ms, Admin54.7/80.2ms; with eight
competing upload requests auth88.7/704ms and Admin79.0/114ms. Decode groups1.193/1.365s. This is
a diagnostic control, not a proposed paid instance or evidence of Render's effective entitlement.

Both4096 runs peaked about292.8 MiB process RSS; no memory max/OOM/kill events. Pillow already runs
in asyncio.to_thread under a one-decoder semaphore, with cancellation holding that gate until its
worker finishes. Ordinary requests are not serialized behind that semaphore. CPU quota contention,
cold imports/query preparation and event-loop/Python scheduling contribute; thread offloading does
not reserve CPU for API work. These observations support CPU throttling/cold-work effects over
memory-limit exhaustion. They do not isolate a particular Pillow operation/GIL path or prove the
old11-second observation was entirely caused by uploads.

1600px/0.1 CPU: peak172.8 MiB, one-decode group7.684s vs13.794s, multiple10.691s vs15.700s. Auth
p95 still2.270s with one decoder and7.100s with competitors. Tail variability prevents claiming an
SLO fix. Smallest existing-infrastructure mitigation: retain serial gate/uploader; one operator/tab
and no parallel retries; pre-size photos to <=1600px and schedule batches during quiet periods.
Warm read-only endpoints before bounded acceptance; this does not eliminate idle spin-down/cold
starts. Keep Production upload capacity UNVERIFIED and do not enable uploads solely on local data.
No runtime changes are required for CI publication. Adding workers/process pools would introduce
memory/lifecycle risk and cannot create CPU entitlement; it is not justified by these samples.

## Integrity and remaining owner gates

Fresh origin/main6851725 remains an ancestor of cdfc863. Approved feature bdcd082 remains clean.
All recorded apps/CI hashes match cdfc863; existing Admin labels/Slider/Merchandise and configuration
are preserved. No later unfinished chatbot commits or new dependencies. Existing build:16 files,
10 forbidden demo markers absent; fixture logins/env files remain ignored, not bundled. Full925/40
frontend and1868/37 backend evidence is reused; no full suites repeated. Documentation-only HEAD
still needs its own exact-SHA hosted CI after any eventual publication.

| Owner gate | Action / current status |
| --- | --- |
| Safe branch publication | BLOCKED: authorize prepared branch-only Vercel suppression, or prove isolated Preview backend/DB/Storage and approve exact-SHA push |
| Supabase Storage/egress | Organization Usage: record used/limit/current period for Storage and cached/uncached egress, all features/backups included; remaining capacity UNVERIFIED |
| Render CPU/memory | Actual worker count, baseline/peak RSS/CPU, cold/steady auth/Events latency and bounded upload headroom; free graphs unavailable/no data, UNVERIFIED |
| Full database/media backup | Verify dated encrypted full app_private + Alembic pin + all media bucket inventory/hashes, off-site copy and recoverable retention; semester backup alone insufficient, OWNER ACTION REQUIRED |
| Isolated restore rehearsal | Existing approved disposable destination; reconcile schema/ACL/RLS/table counts/media keys/hashes and auth/Events/Recap; record RPO/RTO; no restore/new cloud service was performed |
| Dev advisory | Existing GHSA-g3hv-75wg-m249: moderate glob-pattern resource amplification,14 transitive dev audit entries/one advisory; runtime audits clean. Owner risk disposition or compatible tested remediation required for combined release; no new waiver |

Use manual70/85/95% quota thresholds from the prior release report. No subscription, monitoring,
provider or Production operation was changed. Production remains **NO-GO** independently of whether
the CI-only branch path is later authorized. No second UI approval is needed.
