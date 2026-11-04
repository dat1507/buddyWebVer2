# Events Recap pre-release verification - 2026-11-04

**Local RC: READY FOR HOSTED CI. Publication: BLOCKED pending Preview target/isolation verification
and specific owner approval. Production: NO-GO.** No push, main merge, deployment, Production
migration/data write, provider setting, subscription or cloud resource change occurred.

## A. Approved UI - PASS

Owner approved 8/8 categories on `bdcd082aee5c15944bfa0f4060d9219c731062d9`:
Gallery, Details, Admin tabs, Create, Multi-upload, Photos/Thumbnail, Publication, Mobile/EN-DE.
The approved branch/worktree remain clean and unchanged. Nine Recap source/test files are identical
after line-ending normalization; both Recap locale namespaces match exactly. No redesign or new UI
acceptance is required. Current main Admin/chatbot translations and 42 chatbot source files match
main; locks are unchanged. Admin Events differs from main only by the accepted tab import/render.

Approved browser evidence remains applicable to unchanged Recap UI: real local Storage/API workflow
29 checks, four failure paths, 18 EN/DE responsive axe cases with zero violations, loaded screenshots,
focus/keyboard/reduced motion. See [accepted implementation](EVENT_RECAP_LOCAL_REVIEW_2026-11-03.md).
These are prior approved-baseline results, not a fresh hosted/integrated browser run. Browser control
ended with `Debugger unattached`; final hosted responsive/accessibility smoke is UNVERIFIED.

## B. Git integration - PASS

- Approved feature base: `c64fe73e17fedd8d92046bbc7beeedd0a22e2646`.
- Freshly fetched `origin/main`: `6851725362184af7c85828602b6c881f64374b60`.
- Tested source merge: `e77d7182c30397c134c939b1057d3d73b41d675d`; parents are that main and approved feature.
- Branch/worktree: `codex/events-recap-rc`, `.local/worktrees/events-recap-rc`.
- Final branch HEAD is the documentation/test-only successor containing this report/manifest. Resolve its
  exact SHA with `git rev-parse codex/events-recap-rc`; the delivery message records it. Runtime and CI files match the source merge; the final successor only fixes the existing flag-test clock/accessible-name expectation and documentation.

Intervening main commits `35e4ea0`, `c0687ba`, `1e2dbb0`, `6851725` retain the existing default-OFF
chatbot and newer Admin action labels/contextual accessible names. No later unpublished chatbot or
other unfinished branch was merged. Conflicts: adjacent main.py imports and four documentation
prepend conflicts; preserve both imports and dated history. App/locales/Admin auto-merges were
reviewed and tested. Original dirty checkout, security branch, other worktrees and review services
were left in place. [Complete file/commit manifest and evidence](EVENT_RECAP_RC_MANIFEST_2026-11-04.json).

Necessary RC-only changes: safe uncertain-commit upload recovery, three regression cases, stronger
local migration permission assertions, deterministic Admin selectors and flag-test clock, SQL trailing-whitespace
cleanup, and disposable PostgreSQL in CI. No UI behavior or dependency version changed.

## C. Database and compatibility - PASS locally; backup OWNER ACTION REQUIRED

Read-only Production metadata during Nov 3-4 preparation returned
`0021_restore_runtime_permissions`. Disposable PostgreSQL 17 tests pass for fresh install and
`0021 -> 0022_public_event_visibility_default -> 0023_recaps`, including an existing VARCHAR(32)
version column. Alembic environment widens capacity to 128 before the 36-character 0022 revision;
single head is 0023. Final migration/API subset: 12 PASS after SQL whitespace normalization.

Tests verify three private tables, thumbnail ownership/FKs, upload retry/variant/size constraints,
public-order/photo-order indexes, runtime privileges, three runtime-only RLS policies, no
anon/authenticated/service_role SELECT and no runtime TRUNCATE. No Production schema was changed.

Exact deployed Render source `c0687ba8e1253189bd297f60f2d8e8f24e44ecca` ran against a separately
upgraded disposable database. Twelve checks cover liveness, persisted auth, Admin/public Events,
Slider reads, Event create/update/read/delete and absence of old Recap routes. **Compatible before
Recap activation.** A linked Recap fixture confirms old Event DELETE returns 500 from FK RESTRICT,
with Event/Recap rows preserved. Backend rollback after Recap writes requires coordinated write
freeze and forward repair; it is not unconditional backward compatibility. Do not downgrade/drop
Recap tables or media as rollback.

Supabase backup dashboard required sign-in. No available backup/restore proof was obtained.
The existing semester backup is not a full application/Storage backup. The
[off-site recovery plan](../../operations/supabase-free-offsite-dr.md) now explicitly includes
event-media and slider objects, plus Recap tables after migration; its earlier bucket omission is
documented. No backup, S3 configuration or restore was executed. Complete encrypted pre-migration
snapshot, object inventory and disposable restore proof are mandatory before migration approval.

## D. Backend/security - PASS runtime; dev audit FAIL / owner disposition required

Real local API/database acceptance covers ADMIN/current persisted role, CSRF/origin, drafts and
publication, related Event eligibility, ownership/private signed media, stale versions, retry UUID
idempotency, thumbnail fallback/order, cleanup outages/retry/tombstones, image processing and Event
deletion dependencies. Generic Storage reconciliation discovers both derivative references.
No original files, public recap bucket, arbitrary bucket/key input or unrestricted private access.
Previously issued image URLs can remain usable for at most 300 seconds after unpublication; client
reuse is bounded to 240 seconds. Unpublication does not instantly revoke issued capabilities.

Confirmed RC fix: a durable DB COMMIT with lost acknowledgement previously triggered deletion of
its staged image files. Regression reproduces one failure on the old logic; final success,
uncertain-commit and definite-precommit-failure cases all pass. Once COMMIT may have started, retain
files for idempotent retry or existing age-gated orphan reconciliation. Only definite precommit
failures compensate immediately. No automatic orphan deletion was executed.

Pillow 13 and all locked Python runtime/dev dependencies: strict pip-audit PASS, pip check PASS.
Frontend runtime npm audit: zero vulnerabilities. Full/dev npm audit: FAIL, 14 moderate transitive
entries from one existing [minimatch advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249),
no high/critical findings. The advisory concerns attacker-controlled glob patterns; repository
lint/build patterns are reviewed source, and minimatch is absent from runtime dependencies. That
scope assessment is not a new security waiver. The old frontend-only exception does not establish
acceptance for this combined backend/database release; owner disposition or a separately verified
compatible fix remains required. No forced major dependency change was made.

## E. Cost/resource readiness - UNVERIFIED for Production

Reuse existing Vercel, Render, PostgreSQL, private event-media and Pillow; no new paid infrastructure.
Read-only observations: Supabase organization Free; Vercel dashboard Hobby; Render selected Free
0.1 CPU / 512 MB with no scaling. Render metrics showed a different CPU limit label (0.15), so
effective CPU entitlement is unverified; the local probe conservatively used 0.1.

Supabase object metadata: event-media 4 objects / 964,762 bytes; profile-images 5 / 1,013,678 bytes;
combined approximately 1.89 MiB. These aggregates are not billed Storage usage or remaining quota.
Render displayed 4 MB outbound this month. Remaining Storage, egress, compute hours and Vercel
allowance were not verified. Render baseline/peak CPU/memory graphs were Free-plan gated/no data;
**Production upload capacity is UNVERIFIED, not PASS.**

Local 512 MiB / 0.1 CPU probe: real PostgreSQL + ASGI + in-memory Storage, chatbot OFF, one 4096x4096
decode alongside auth/Events reads; peak process RSS 282.8 MiB, cgroup memory.peak 274,448,384 bytes,
OOM/kill counters zero. Peak accounting differs between process/cgroup and is not available
Production headroom. A second Recap upload returned 429; only one Recap decoder per process is
admitted. Liveness 0.025s, Slider 6.657s, public Events 7.470s, auth 10.274s, Admin Events 10.594s;
maximum-size decode/concurrent group 18.102s. This demonstrates CPU contention, not Production
latency acceptance. Other image workloads, workers, real Storage/network, traffic and actual
Production baseline were not modeled. Do not enable Production uploads on this evidence alone.

Planning assumption: ten photos/Recap, 350 KiB display + 40 KiB thumbnail per photo:

| Recaps | Additional stored derivatives |
| --- | ---: |
| 10 | 38.09 MiB |
| 30 | 114.26 MiB |
| 50 | 190.43 MiB |
| 100 | 380.86 MiB |
| 200 | 761.72 MiB |

First 10-30: 100-300 uploads, 200-600 objects. Prior already-compressed five-WebP sample averaged
183,791 derivative bytes/photo versus 178,068 source bytes; two derivatives can increase storage.
No universal compression saving is claimed. Monthly list/detail assumptions (14 thumbnails/list,
10 thumbnails + two display images/detail): 1,000/100 views approximately 0.64 GiB and 16,300 API
requests; 10,000/1,000 approximately 6.39 GiB/163,000; 100,000/10,000 approximately 63.90 GiB/1.63M.
Signed-URL renewal, retries, other features and backups add cost. Quotas must be compared with total
project use. Manual thresholds: 70% review forecast; 85% investigate capacity/uploads; 95% stop
additional consuming operations pending owner review. No paid monitor or automatic upgrade.

Owner checks: Supabase organization Usage (Storage, cached/uncached egress, database) and project
Database > Backups; verify date, retention and restore method privately. Render service Metrics and
Usage/Billing: baseline/peak RSS/CPU, outbound, hours, worker count and healthy bounded-upload
latency. If Free metrics are unavailable, provide owner-approved zero-cost evidence or keep this
gate open. Vercel team Usage: transfer/build allowance. Record aggregate used/limit/period only.

## F. Verification - PASS local; hosted UNVERIFIED

| Gate | Final local result |
| --- | --- |
| Frontend full suite | 925 PASS / 94 files / zero fail or skip |
| Backend full suite | 1,868 PASS / 37 existing opt-in SKIP / zero fail |
| Frontend formatting, ESLint, TypeScript | PASS |
| Backend Ruff, strict mypy | PASS / 328 source files |
| Alembic head/history, fresh/0021 upgrade, permissions/API | PASS |
| Runtime Python/dev audit and frontend runtime audit | PASS |
| Frontend full/dev audit | FAIL: existing 14 moderate entries / one advisory |
| Frontend production build, disabled/enabled Event flag matrix | PASS; four flag combinations / 40 focused cases |
| Wheel/sdist, pinned production Docker build | PASS |
| Actual production image | non-root UID10001, Pillow13, Recap imports, liveness200 PASS |
| CI YAML + Docker Compose | PASS; contents read-only; disposable postgres service |
| Demo/mock exclusion | 16 built files / 10 forbidden demo markers absent; production Slider mocks gated by DEV |
| Approved accessibility/responsiveness | Prior 18 axe cases PASS; source identity preserved; final hosted smoke UNVERIFIED |

Main baseline 920 frontend tests becomes 925: seven Recap cases minus two obsolete placeholder
cases. Approved older feature branch was 838 plus two late timezone cases (840); main brought 85
chatbot tests. Backend main 1,855 becomes 1,868: eight image cases, two enabled local live cases and
three commit-recovery cases. All 37 skips are pre-existing external-service opt-ins; neither new
Recap live test is skipped. One existing Starlette/AnyIO deprecation warning remains.

Initial full runs exposed an ambiguous/stale Admin translation selector, a 1s onboarding wait under
host contention, and a 15s old chatbot CLI import timeout on Windows bind mounts. Admin selectors
now wait for the actual table; production behavior is unchanged. Onboarding/CLI pass unchanged in
isolation and final full suites. Final frontend bounded to four workers; backend used identical
source copied to Linux filesystem. No test retries, timeout increases or skip additions. Final
strict-import-only test correction and SQL whitespace cleanup received focused 3/12 PASS plus full
static checks; unchanged full suites were not repeated. The enabled-flags follow-up also exposed a pre-existing stale Dashboard accessible-name expectation and
November1 upcoming-event fixture that had expired by the session date. Pinning only Date to October31
in that test makes its intended upcoming-event case deterministic; all four flag combinations were rerun. Evidence remains in ignored local
`.local/rc-evidence`; credentials/env/login files stay private and untracked.

## G. Hosted preparation, rollout and recovery

GitHub Actions push/PR runs frontend/backend gates; it has no deploy command. The only added service
is PostgreSQL inside the runner, with an explicitly disposable local-only credential. It is not a
cloud database or a Production secret. Exact-SHA remote CI has not run because nothing was pushed.

Fresh Vercel metadata at 2026-11-04 local reports Production READY/main/6851725, deployment
`dpl_2bmuqvAyM1RnJrCZhVdupmMXBza3`. Preview dashboard tracks all unassigned branches, no domains
attached. Candidate branch should produce Preview, not Production; Production branch configuration
still needs a final pre-push confirmation. Detailed team-scoped requests returned403; default-scope
read-only project/deployment inventory succeeded. Preview API-target reveal required owner
verification and was cancelled without sending a code. Its target/isolation remains UNVERIFIED.
Before publishing, owner must confirm Vercel Settings > Environments > Production branch=main,
Preview tracking/no Production domain, and Preview `VITE_API_URL` points to a verified isolated
backend/database/Storage. Do not expose its value in Git/chat. Do not log into or perform writes
through a Preview with an unknown/shared Production API target. An isolated local backend is not
reachable from hosted Preview without a separately approved arrangement. No new hosted backend
or tunnel was provisioned. Render live c0687ba, branch main, apps/api Dockerfile, health
/api/health/live, Auto-Deploy OFF were directly observed; preserve OFF.

After Preview isolation/trigger checks, request approval to push **only** `codex/events-recap-rc`
at its exact final SHA for GitHub CI/Vercel Preview, without main merge or Production deployment.
Then require exact-SHA hosted checks and integrated read-only/isolated functional acceptance.
Production needs a separate request after every critical gate below is closed:

1. Recheck current main/Production pins and candidate diff; keep chatbot/other flags at accepted
   baseline. Approve full backup operation; verify encrypted snapshot and disposable restore.
2. Separately approve migration. Pin candidate Alembic code/owner credential; upgrade from verified
   current revision through 0022 then 0023. Verify head, version capacity, grants/RLS and counts.
3. Keep current Vercel frontend/Recap placeholder. With Render Auto-Deploy OFF, separately approve
   manual deployment of the exact candidate backend. Verify readiness, persisted auth, existing
   Events/Slider/profile flows and new public Recap reads before any new Recap writes.
4. Separately approve the candidate frontend build with correct public API and existing Events
   flags. There is **no dedicated public Recap flag**: deploying this frontend replaces the
   placeholder and activates public `/events/recap` independently of `VITE_PUBLIC_EVENTS_ENABLED`.
   Admin routes depend on existing `VITE_ADMIN_EVENTS_ENABLED`. Do not deploy frontend first.
5. Read-only Production smoke: liveness/readiness, Landing/Slider/Event detail, Recap list/detail,
   EN/DE/mobile, auth and prior user/Admin navigation. No unauthorized account or content writes.
6. Only after explicit owner-approved functional write acceptance and capacity disposition:
   bounded upload/create/publish/unpublish/delete using approved records, monitor thresholds and
   record evidence; do not infer approval from prior local UI acceptance.

Rollback: before Recap writes, revert frontend and manually restore verified prior backend c0687ba;
leave additive schema in place. Before changing backend, verify prior image/deployment availability.
After writes, frontend rollback hides new entry points but does not remove data or prevent direct
API access. Freeze relevant writes and keep/forward-fix the Recap-aware backend; old c0687ba Event
deletion is unsafe for linked Recaps. Preserve tables, audit and media; retry cleanup deliberately.
Backup restoration is a separately approved incident action with reconciled data loss/RPO and
Storage inventory, never a default destructive downgrade.

## H. Critical gate disposition

| Gate | Status |
| --- | --- |
| Approved 8/8 UI and current main integration | PASS |
| Local runtime/security/migration/regression/build | PASS |
| Pre-activation old backend compatibility | PASS; conditional rollback limit documented |
| Dev dependency advisory disposition | OWNER ACTION REQUIRED (audit FAIL retained) |
| Full backup and restore proof | OWNER ACTION REQUIRED |
| Actual quotas and Production upload capacity/latency | UNVERIFIED / OWNER ACTION REQUIRED |
| Preview API isolation and final branch trigger check | OWNER ACTION REQUIRED; publication BLOCKED |
| Exact-SHA GitHub CI/Preview/browser acceptance | UNVERIFIED |
| Production backup/migration/backend/frontend/write approval | BLOCKED; not requested or granted |

Local preparation is complete. **READY FOR HOSTED CI describes the local candidate, not permission
to publish. READY FOR PRODUCTION: NO. Production NO-GO remains in force.** Next is owner verification
of Preview configuration/isolation, followed by specific candidate-only publication authorization.
