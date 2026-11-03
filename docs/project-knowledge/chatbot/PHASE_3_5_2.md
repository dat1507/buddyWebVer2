# Phase 3.5.2 — final candidate acceptance

2026-11-03 Asia/Saigon. CHATBOT-ACCEPT-001. **PARTIAL / RELEASE NO-GO.**
Starting candidate35e4ea0f9b42fddb99d8a451cdb403c09cd5b1a3, branch
codex/chatbot-phase35-integration. Clean at entry. Fresh remote main and Vercel public Production
both c64fe73e17fedd8d92046bbc7beeedd0a22e2646; candidate1 ahead/0 behind. No baseline drift,
merge, rebase or source correction. Final successor is documentation only; resolve its SHA with
`git rev-parse codex/chatbot-phase35-integration`. App/knowledge/locks/CI/legacy blobs stay unchanged.

## Verified local acceptance

Existing optimized ON preview5197 served explicit dist/integration-on, API base127.0.0.1:8035/api.
A fresh exact-source `npm run build -- --outDir dist/phase352-on --manifest` passed; hashes of all9
served JS/CSS/HTML/manifest files match the fresh output. `git diff35e -- apps` empty. Docker
fixture reused the previously verified production image, unchanged backend source, internal-only API
network, loopback relay, non-root/read-only/capped512MiB; no DB/provider env or inference. Process
commands used explicit repository working directories/strict ports. Initial sandbox preview timed
out; external loopback launch/reload succeeded. URL, build hashes and real API behavior agree.

All eight required questions were exercised through the browser: EN/DE registration chose verified
FAQ; food and laundry returned qualified owner evidence; `eat` and `Wäscherei` qualified inferred
intent; German original English passages explicitly untranslated; Mars returned insufficient
information with no fabricated citation. Laundry details displayed actual source0fe1c16900d4,
lines420–421. Existing17 FAQ/nine JSON/canonical source and intent rules unchanged. No facts added.

EN and DE settled responsive checks at1440/768/390/320: no log horizontal overflow; desktop/tablet
region, mobile modal/inert background; mobile bounds within subpixel rounding (<1px at390).
Reduced-motion emulation produced0s panel animation; overrides reset. Three repeated close/open
cycles completed. Escape restored launcher focus and cleared inert. Loading state observed.
Actual network outage showed safe retry; default-OFF API showed friendly503; restartingON and
retrying returned verified registration. Bounded local31-request quota exercise returned29x200,
2x429; subsequent German browser request showed cooldown/retry text. No Production load traffic.
Automated keyboard/focus/safe rendering/flags evidence is reused from Phase3.5.1; exhaustive new
keyboard traversal and cooldown-expiry timing were not independently repeated. Physical keyboard/
virtual keyboard and hardware screen-reader acceptance remain MANUAL PENDING. No automated axe
scan was added or claimed. Visual screenshots inspected; native browser capture is supplementary
to settled DOM measurements. Screenshots live outside Git in the session visualization folder.

No expensive suite rerun: unchanged application retains1,855 backend PASS/37 opt-in live skips,
920 frontend PASS/91 files,129 affected PASS, Ruff/mypy318/TS/lint/format, ON/OFF builds, wheel/
pip integrity, Docker Python3.12.14/uid10001/Pillow13/37pins, runtime audits0, prior38 HTTP checks.
These are reused exact-source evidence, not newly executed CI. Owned previews/containers/network
stopped; unrelated services/worktrees left alone. Local browser JSON/build identity retained ignored
under .local/phase352; raw logs/credentials/personal account data are not committed.

## Hosted evidence and limits

VERIFIED HOSTED CONFIGURATION: Vercel public alias stillREADY c64, deployment
`dpl_9qn8NtQWwGGer9kNxQGn9QFkCyyK`. Prior fixed5a deployment
`dpl_EU19m7DJSsrbHNc2CvAZVX53LusX` independently remainsREADY. Rollback-candidate listing
returned403; no Vercel/gh CLI installed for fallback. Retention existence is not rollback eligibility.
Render signed-in settings: Live642fc11eb6fe206b95e383c8585a4ae1ad066e78, root apps/api,
Dockerfile ./Dockerfile, command override empty, health /api/health/live, AutoDeployOff and
PRPreviewsOff. Compute page shows Free0.1CPU/512MB and no Free scaling. Current release is
independently observed, not inferred from the frontend SHA. Prior backend artifact/rollback
eligibility UNVERIFIED. No edit/deploy/upgrade action or secret reveal performed.

Local Docker CMD uses proxy headers with restrictive127.0.0.1 allowlist and no-access-log. Actual
Render socket peers, header overwrite/sanitization and effective WEB_CONCURRENCY/env are unknown.
Do not infer reliable per-person anonymous limiting: process-local quotas multiply by workers,
reset on restart, share NAT buckets, and may collapse clients if the real proxy is untrusted.
UNVERIFIED – HOSTED PROXY ACCEPTANCE REQUIRED. No `*` forwarding trust or guessed ranges added.
Direct HTTPS API topology from retained configuration remains; exact current CORS/host/env values
were not revealed. Local CORS tests do not certify deployed settings.

Official documentation, separately from account evidence:
[Render Free](https://render.com/docs/free) specifies15-minute idle sleep,750 shared instance-hours
per workspace/month and included outbound/pipeline allocations. [Render logging](https://render.com/docs/logging)
states dashboard retention depends on workspace plan and public HTTP request logs are available
on Pro workspaces or higher. These do not prove the actual workspace tier, edge retention, body/
cookie/header redaction or log-stream configuration. Service Free compute is not workspace-plan
proof. Local app metadata-only/no-access-log tests cannot establish end-to-end hosted privacy.
No real user log contents were exported or printed. Hosted privacy remains UNVERIFIED.

ESTIMATED:100 questions/day is about0.00116 average requests/sec (3,000 per30days), modest compared
with the local bounded sample. Prior memory sample85.34MiB is below512MiB, but used1CPU rather
than Render0.1CPU and excluded full hosted workload; it is not a capacity guarantee. Shared free
hours, existing usage, bandwidth, pipeline allowances, billing controls and alerts remain unknown.
Zero-cost feasibility ESTIMATED / owner monitoring required, not a confirmed allocation guarantee.
Safe fallback: keep chatbotOFF if quota headroom cannot be accepted; never upgrade or add keepalive
traffic/paid monitoring automatically. No paid resource or external AI inference used during review.

## CI and recovery

VERIFIED LOCAL: sole .github/workflows/ci.yml runs on push and pull_request. Frontend performs
install/format/lint/types/test/build/runtime audit; backend Python3.12 locked install/pip integrity,
Ruff/mypy/pytest/Alembic graph/package/audit/Compose validation. No workflow_dispatch entry exists.
Exact unpublished SHA cannot acquire remote CI evidence without separately authorized publication;
remote CI BLOCKED by explicit no-push/no-trigger instruction. Local tests are not hosted CI.
Public branch-protection lookup401; required-check/ruleset/billing eligibility unknown. Prior
hosted trigger evidence says main pushes can deploy Vercel Production and other branches Preview;
Render AutoDeployOFF freshly confirmed. Reconfirm Vercel trigger policy before any publication.

UNVERIFIED – ROLLBACK TARGET ACCEPTANCE REQUIRED. Current fixed frontendc64/prior5a and current
backend642 are identifiers to verify for a future recovery, not executed recoveries. Check retained
artifacts and env compatibility; do not restore pre-Pillow13/Zod fixes. Knowledge recovery uses a
reviewed prior deployment/source commit, no ephemeral filesystem edits. No rollback executed.

## Release gate matrix

| Gate | Status / evidence category |
| --- | --- |
| Git baseline | PASS — fresh remote/Productionc64; local candidate aligned |
| Local integration | PASS — VERIFIED LOCAL, unchanged exact source |
| Browser acceptance | CONDITIONAL — VERIFIED LOCAL core flow/responsive/errors; exhaustive keyboard/cooldown-expiry pending |
| EN/DE chatbot | PASS — VERIFIED LOCAL eight real UI/API questions and provenance |
| Proxy trust | UNVERIFIED — hosted peer/header acceptance required |
| Rate limiting | CONDITIONAL — VERIFIED LOCAL; hosted worker/NAT policy unaccepted |
| Logging/privacy | UNVERIFIED — local protection passes; provider retention/config unknown |
| Knowledge packaging | PASS — reused VERIFIED LOCAL exact source/container evidence |
| Runtime | PASS — reused VERIFIED LOCAL Linux/package results |
| CI | BLOCKED — exact candidate not published; no remote CI trigger authorized |
| Feature flags | PASS — VERIFIED LOCAL actualOFF503/ON recovery plus prior OFF build |
| AI isolation | PASS — VERIFIED LOCAL disabled providers/internal API network |
| Hosting quota | UNVERIFIED — ESTIMATED fit; actual free allocation/usage not established |
| Accessibility | CONDITIONAL — local checks pass; physical-device/SR acceptance pending |
| Rollback | UNVERIFIED — retained FE artifact observed; eligibility/backend target unconfirmed |
| Deployment authorization | BLOCKED — explicitly not granted |

Decision **NO-GO**, because critical hosted trust/privacy/quota/recovery uncertainty remains.

## Owner checklist before Phase3.6

1. Render service Settings/Environment: inspect effective worker count and forwarding settings
   privately. Obtain provider-backed peer/hop and header replacement guarantees. In separately
   approved isolated Preview, compare two controlled clients and spoofed headers using only
   redacted equality results; never log personal IPs or widen trust to * as a diagnostic shortcut.
2. Render workspace Usage/Billing and service Metrics: confirm workspace plan, remaining shared
   free hours/bandwidth/pipeline, observed CPU/memory and no paid escalation; accept cold starts
   and process-local/NAT/restart limits for100 questions/day. KeepOFF if uncertain.
3. Render Logs/Settings/Log Streams and Vercel Observability/Logs: privately inspect actual retention,
   destinations and redaction. Obtain provider confirmation where UI does not expose behavior.
   In approved preview use synthetic sentinels, never real cookies/questions; record only booleans.
4. Vercel project Deployments/rollback eligibility and Render Deploys: confirm retained security-fixed
   compatible FE/BE targets and env implications; do not click Rollback/Deploy during acceptance.
5. GitHub Settings Rules/Branches and Actions usage: confirm required checks and quota. Vercel
   project Git/Environment: confirm Preview vs Production triggers. Approve an exact branch/SHA
   publication procedure separately, with auto-preview effects stated; then verify exact hosted CI.
6. Finish physical-device/SR, exhaustive keyboard traversal and cooldown-expiry checks. Only after
   critical gates close, approve a separate flag-OFF deployment, backend enablement, frontend rebuild
   and tiny public EN/DE smoke. No publication or release authorization is implied by this report.
