# Phase 3.5.1 — safe integration and release gates

2026-11-03 newer continuation: [Phase3.5.2](PHASE_3_5_2.md) closes exact-candidate core browser
acceptance. Updated sixteen-gate matrix and precise owner acceptance checklist are authoritative;
Production remains NO-GO. Prior evidence below remains historical; no push/deploy authorized.

2026-11-03, Asia/Saigon. [CHATBOT-INTEGRATE-001](../../implementation/tasks/CHATBOT-INTEGRATE-001.md).
**Local integration verified; overall PARTIAL; Production NO-GO.** No push or deployment.

## Git inventory and integration decisions

Final approved baseline: `c64fe73e17fedd8d92046bbc7beeedd0a22e2646`, verified remote main and
fresh Vercel Production. Initial5a7bb90 was valid at intake; remote advanced concurrently. Common ancestor: `f88c18dbc8cf5f62ff1e4184b9ad38375b1faab2`.
Prior Phase 3.5: `a1aa0ad1def924403c395e9cf6b2278fb3f44a7d`, now protected by the new local
`codex/chatbot-phase35-preserved` ref. Its detached checkout remains unchanged.
Isolated candidate: `codex/chatbot-phase35-integration`, one local commit on approvedc64. Resolve its
exact final SHA with `git rev-parse codex/chatbot-phase35-integration`; this report belongs to it.
The candidate selectively integrates content; it does not merge/move the divergent local main.

| Existing checkout/ref | Preserved HEAD / original state |
| --- | --- |
| Primary, codex/pillow-security-fix | 8c02dfb; seven dirty tracked documentation files; 201 visible untracked files |
| Local main | 9ec31fb; initially six ahead/four behind; now six ahead/five behind, local ref unchanged |
| Prior chatbot-phase35 | a1aa0ad, clean/detached |
| pillow-hotfix-rc | 642fc11, clean |
| security-main-sync | e1a2cc59, clean |
| landing-redesign | 7749ea8, clean |
| ui-consistency-demo | c1e04e9, clean |
| ui-release-rc | 5a7bb90, clean |

Primary preservation includes 256 fingerprints:172 skills/resources,82 documentation,2 other;
48 Architecture-Study files are ignored by existing Git exclusion but were also fingerprinted.
There were no staged changes, dirty application files, conflicts or incomplete Git operations.
Existing heads/tags, indexes, dirty/untracked bytes and worktree states are compared against the
pre-integration manifest. All256 hashes matched at the first completed preservation checkpoint.
During the concurrent c64 publication, five primary control-plane documents changed externally
(SESSION_HANDOFF.md, implementation-plan.md, validation.md, task-index.md, production-status.md),
and an untracked FE-EVENT-MERCH-001 extract appeared (visible untracked count201→202). This task
never wrote those primary files; their newest contents are retained. Final comparison:251 hashes
unchanged, five external documentation updates preserved, no original file missing; all original
worktree HEADs/indexes and original refs unchanged. Do not restore the older manifest over them. No reset, rebase, clean, forced ref update or branch
deletion; no worktree was removed or archived.
Safe fetch used an explicit non-force main refspec, with no pruning/tags. Original main is untouched.
A concurrent Event/Merchandise branch/main update appeared at c64fe73. A fresh read-only connector
confirmed it is current Vercel ProductionREADY. This task did not push it. Our isolated work was
retained in a safety stash, the integration branch fast-forwarded normally, then the task work
reapplied. The stash is retained, never dropped. Only the task-index count conflicted; resolution
keeps all upstream/task rows (248 total). All previous refs and original worktrees remain intact.
Current Event navigation/Merchandise source/tests/styles and new descriptions are byte-preserved;
frontend regressions/build/static checks rerun for this new combined source. Backend tree/pins are
unchanged by c64, so the completed Linux backend/image gates are reused, not rerun.

57 approved application paths were audited against both branches from the common ancestor.
54 non-overlapping paths were copied from approved Git blobs only after checking baseline identity
or absence. Three overlapping paths received selective additions:

| Path | Resolution |
| --- | --- |
| apps/api/pyproject.toml | Retain all5a configuration/Pillow13; add only chatbot package-data table |
| apps/web/src/locales/en/common.json | Add chatbot namespace; preserve every other current value |
| apps/web/src/locales/de/common.json | Add chatbot namespace; preserve every other current value |

Existing released UI (including c64 Event/Merchandise), App business routes, auth/security, Pillow13, Zod4.6.6, dependency locks and
CI files remain intact. App only imports/mounts the approved chatbot entry; transport changes stay
scoped to public chatbot requests. Seven prior chatbot task extracts and17 knowledge records were
imported with historical evidence intact. Legacy archive is unchanged. No blanket cherry-pick/merge.

Two narrow integration adjustments: exclude `.local` from Docker build context; calibrate one test's
50ms deadline to1000ms for measured mounted-Linux first-route initialization (~156ms). The test still
runs a ten-second body and asserts504, cancellation and subsequent200 with concurrency1. Production
2000ms default and all runtime logic are unchanged. Other timeout/retained-worker assertions remain.
An intermediate Windows test-edit encoding error was corrected from exact approved UTF-8 blobs;
only the intended deadline/comment diff remains. No factual source or vocabulary edit.

## Knowledge and artifact integrity

Canonical systemPrompt.txt: **22,129 bytes /431 lines**, SHA256
`0fe1c16900d47c2c57e50d56cdc3ee4b2bd66dc9d6b2ccd2366256162519f0a8`.
Exact approved bytes; nine JSON corpora unchanged,17 verified FAQs, two historical references and
nine historical exclusions unchanged.174 parsed passages:147 owner-provided,6 conflicted,
17 sensitive,4 instructions. Owner material remains conditional/unverified; conflicts are labeled,
sensitive/instruction material is withheld. German qualification is localized; original English
quotes are explicitly untranslated. No invented translation, fact, current verification or citation.

Actual Dockerfile build: `buddyweb-chatbot-integration:20261103`, local only. Manifest digest
`sha256:bb3179c4e48be971e49302b0de44cb08f0ccf36442963a7bd66754a5b2590626`.
Runtime Python3.12.14, uid10001, Pillow13.0.0;37 locked runtime pins match. Installed chatbot
modules/source/JSON match checkout. Unrelated-cwd CLI and knowledge loading pass inside the image.
Wheel build/install and pip integrity pass in a new isolated local environment. No shared env edits.

## Release gate matrix

| Gate | Local evidence | Hosted disposition |
| --- | --- | --- |
| Git integration | PASS; protected prior commit, approvedc64 baseline, selective delta, original work preserved | Candidate unpushed; exact hosted CI UNVERIFIED |
| Linux/runtime | PASS; actual production Docker build/probe, non-root, exact pins/package/source; full regression below | Deployed candidate acceptance UNVERIFIED |
| Routing/proxy | PASS local transport and trusted/untrusted/multi-hop/IPv6 tests | Actual Render peer CIDRs/hops/header overwrite guarantees UNVERIFIED; NO-GO |
| Rate limits | PASS client/global caps, TTL/bounded buckets, concurrency/deadline/cancellation,38-request real HTTP check | Process-local/NAT/restart limitations need owner acceptance; no distributed guarantee |
| Logging/privacy | PASS actual no-access-log CMD and synthetic query/body non-retention in captured Docker logs | Edge/platform retention and effective hosted logging UNVERIFIED; NO-GO |
| Knowledge packaging | PASS exact files/hash/passages inside built image and unrelated cwd | Production source version not yet deployed |
| Feature flags | PASS default backendOFF, frontendOFF hides launcher, ON UI/backendOFF friendly message, ON/ON real answer | Future approved staged toggle/rebuild only; AI remainsOFF |
| Accessibility/UI | PASS101 chatbot tests; full frontend 920; initial5a EN four-width/source/Escape/focus evidence | Finalc64 browser, DE/screenshot, real-device and screen-reader acceptance UNVERIFIED |
| Cost/AI isolation | PASS retrieval only, AI=true fails closed, direct artifact socket/provider guards0; HTTP API has internal-only network | Existing RenderFree observed; current quotas/scale acceptance UNVERIFIED; no upgrade authorized |
| Rollback | Current security-fixed FEc64 and BE642 deployment identifiers verified read-only; proposed disable/rollback procedure | Retention/eligibility and actual recovery NOT EXECUTED; recheck before release |

Do not widen trusted forwarding to `*`, add guessed provider ranges, trust raw leftmost XFF, add
Redis/paid resources or change unrelated authentication to make a gate green. Keep flags OFF until
critical hosted gates and explicit publication/deployment permission are resolved.

[Exact commands and harness boundaries](PHASE_3_5_1_COMMANDS.md).

## Executed validation and limitations

| Check | Result |
| --- | --- |
| Focused backend security/chatbot | 494 PASS,92.96s; included image-storage/rate/observability regressions |
| Full Linux Python3.12 backend | 1,855 PASS /37 opt-in infrastructure SKIP,187.69s (final exact UTF-8 fixtures) |
| Focused frontend transport/widget | 101 PASS /4 files,27.36s initially; finalc64 chatbot/Event focus129 PASS /7 files,44.41s |
| Full frontend | 920 PASS /91 files,633.75s; finalc64 combined source |
| Ruff / strict mypy | PASS /318 files PASS |
| Frontend TypeScript / ESLint / final Prettier | PASS /PASS /PASS |
| ON and OFF optimized builds | PASS on finalc64,3.48s/3.56s; approved lock, loopback target;18 build files exclude all10 demo markers |
| Wheel / dependency integrity | PASS /No broken requirements |
| Runtime audits | npm0 vulnerabilities; Python36 audited/0 skipped/0 known vulnerabilities |
| Actual Linux image/probe | PASS; defaultOFF, AI fail-closed, exact files/pins,7 representative EN/DE questions |
| Actual isolated HTTP | 38 chat requests:23x200,1x400,2x422,1x413,3x503,8x429; CORS allow/deny PASS |
| Unrelated HTTP health/auth | Four concurrent liveness200; final liveness200 and anonymous auth401 |
| Resource sample | Chat p95 212.62ms; max concurrent health189.77ms;79.54→85.34MiB /512MiB;1CPU cap |
| Preservation / task-path coverage | PASS:7 original HEADs/indexes; initial256 hashes matched; final251 same/five external doc updates retained;248 task paths; original refs unchanged |

Three503s in the concurrent burst are intentional bounded admission rejection, not retrieval errors.
Rotating raw XFF/X-Real-IP does not evade the local peer's30/60s cap; Retry-After/no-store verified.
Default global cap300/60s,2 workers,2048 client buckets,500 chars/4096 bytes,2s deadline.
This tiny sample is not a Render capacity/SLA claim and does not establish real proxy identity.

The HTTP API ran read-only, non-root, capped1CPU/512MiB, on an internal network with no external
egress; a byte-only loopback relay resolved Docker Desktop's internal-network publishing behavior.
No provider credentials, database configuration, real account or AI call was used. No actual HTTP
provider-attempt counter is claimed; separate direct guards and tests verify prohibited paths.
Captured synthetic Docker logs omit query-marker/body text; raw logs remain ignored locally.

The first full Linux run found a50ms test-budget failure; subsequent calibration removed cold
initialization assumptions without dropping assertions. A wrong initial mount caused collection
errors and was corrected to whole-repository read-only layout. These attempts are not PASS evidence.
Final UTF-8 run is authoritative.37 opt-in database/Redis/live tests are skipped, not accepted.
Known baseline large-chunk and AnyIO deprecation advisories remain. Existing scoped dev minimatch
exception/follow-ups are retained; this task audits runtime dependencies only and claims no dev0.

Real browser on the initial5a-based integration observed the released landing UI plus owner food answer and exact
source lines/hash. Source expansion worked. EN desktop/tablet panel400px;390/320px mobile dialog,
background inert, no horizontal chat overflow; Escape restored launcher focus and cleared inert.
Subpixel rounding at390 was under1px. Browser control then stopped because current URL could not
be verified reliably on Windows. No further browser automation was attempted. German browser flow,
remaining keyboard/reduced-motion live checks and screenshot capture are explicitly UNVERIFIED;
automated localized/focus/reduced-motion tests pass. The later c64 candidate has no fresh browser
acceptance; do not relabel the earlier5a screenshots/observations as final-source evidence. Temporary
agent tabs close at turn cleanup.

Owned API containers, relay and empty internal network removed. Only task-owned frontend preview
processes are stopped; no user container/service/worktree is deleted. Docker Desktop was started
locally for these checks and left running because seven unrelated user containers are active; none
was stopped or removed by this task.

## Fresh read-only hosting evidence —2026-11-03

Vercel initial alias observation: READY/main5a7bb90/dpl_EU19m7DJSsrbHNc2CvAZVX53LusX.
Later same-day public Production alias www.vgubuddyprogram.com: READY/mainc64fe73, projectbuddy-web-ver2,
deployment `dpl_9qn8NtQWwGGer9kNxQGn9QFkCyyK` (supersedes the initial frontend snapshot). Render vgu-buddy-api-production: Docker/Free,
Live642fc11 (`642fc11eb6fe206b95e383c8585a4ae1ad066e78`), main,
deployment `dep-dbhhnpp42hec73cgjsu0`; Auto-DeployOFF and PRPreviewsOFF. Root apps/api,
Dockerfile ./Dockerfile, build context `.`, command/predeploy overrides empty, health /api/health/live.
Source: signed-in settings read-only, no Edit/Deploy/reveal or real request log inspection. Actual
peer chain, effective env/worker count, edge logging/retention, quotas and rollback eligibility remain
unverified. No new Production health/auth/runtime acceptance is inferred from these settings.

The retained isolated-work safety stash is `d146843d0114a822d123a744fbe6df0ae18d09fd`; it
contains the pre-c64 task work and was applied by exact hash, not popped or dropped. It does not
contain or stash original primary user work.

## Release decision and next acceptance

**NO-GO.** Git integration and the prior local Linux artifact gap are closed. Critical hosted proxy
identity and logging/privacy acceptance, exact candidate hosted CI, and controlled deployed smoke
remain open. Browser/device/SR gaps and process-local load/quota acceptance are also explicit.
Zero additional operating cost, no inference, new paid resource, cloud/data/secret/config mutation,
remote push or deployment. This is a reviewable local release candidate, not release authorization.

Use the [updated Phase3.6 runbook](PHASE_3_6_RUNBOOK.md). Next: finish finalc64 EN/DE/browser/screenshot/device/SR checks,
obtain provider-backed peer/header and privacy/retention evidence, confirm quotas/worker count and
security-fixed rollback eligibility; then seek exact candidate publication permission with automatic
Vercel trigger effects stated. Only after green hosted CI and separate release approval may a
flag-OFF deployment, staged backend/UI enablement and tiny public EN/DE smoke occur. Never publish
old local main9ec or the preserved detached candidate as a replacement for current main.
