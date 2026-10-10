# Session handoff

**Updated:** 2026-10-11 (Asia/Saigon)
**TASK_ID:** EVENT-FLAG-SPLIT (RELEASE CANDIDATE — LOCAL GATES PASS / BOTH PRODUCTION FLAGS OFF)
**Current mode:** Controlled frontend release; stop before Admin-only activation or any Event write
**Repository:** `C:\Users\phuoc\Downloads\buddyWebVer2`
**Branch:** `main`

## Continue from here

`EVENT-FLAG-SPLIT` is the active approved task. The frontend now uses independent strict
`VITE_ADMIN_EVENTS_ENABLED` and `VITE_PUBLIC_EVENTS_ENABLED` build-time switches. Exact `true` is
the only enabling value; missing/invalid values are OFF, and `VITE_EVENTS_LAUNCH_ENABLED` is ignored.
Admin list/create/edit/navigation/metrics share the Admin switch, while Landing live data, public
detail and User Event surfaces share the public switch. Disabled direct routes render a consistent
404 without bypassing the existing USER/ADMIN role guards.

Final local verification on 2026-10-11 is PASS: resolver 11/11; focused affected tests 67/67; each
of four Admin/Public combinations plus missing/legacy and invalid/legacy matrices passes 8/8;
full frontend 85 files / 788 tests; TypeScript, ESLint and Prettier PASS; all four production-build
combinations PASS. The final OFF/OFF bundle retains all five static titles and contains neither the
live slider endpoint marker nor `/admin/events`. No backend code/dependency changed, so prior backend
CI evidence is reused.

Production preflight confirmed the `buddy-web-ver2` Vercel project in the expected team, current
READY deployments and absent Admin, public and legacy Event keys. Both features will therefore stay
OFF after the authorized `main` rollout. Render requires no new backend deploy; preserve its accepted
`e2ef4c0` live and `d15cb1d` rollback evidence. Run only read-only OFF/OFF Production smoke, then
stop at **AWAITING ADMIN ACTIVATION**. Do not add either flag, create/upload/publish an Event, or
change database, Storage, Redis, DNS, secrets or provider configuration.

The large legacy plan has been split into a lightweight control plane plus per-task extracts. Start
with `implementation-plan.md`; do not scan `implementation_plan_vgu_buddy.md`.

`FE-LANDING-BG-002` is DONE / PRODUCTION VERIFIED. The owner confirmed the corrected Production
slideshow is smooth. Source commit `c2fbaf1` reached `origin/main`;
GitHub/Vercel deployment `6952736000` and both repository checks succeeded. Public bundle
`index-CC-xLBAH.js` passed a 15-transition/three-loop desktop audit plus mobile, reload and reduced
motion checks with no blank sample, undecoded-visible image, visible-layer source swap, layout
delta, overflow or console warning/error. Do not repeat these gates without a regression reason.

The owner also confirmed that Home University displays correctly in the Production Profile UI.
The original edit/save/reload/clear/max-length gate remains open, so
`FE-PROFILE-HOME-UNI-001` is not DONE.

The owner selected the dynamic Event lane. The canonical chain from `EVT-005` through `FE-014B` is
implemented and deployed from `e2ef4c0`. It uses one Event source: the Landing slider
derives PUBLIC/PUBLISHED/upcoming Events with ready covers; there is no standalone Slider
admin/table or manual ordering. Per the latest owner decision, Landing renders the first five
canonical API results; the backend 12-row bound remains an API/query cap rather than an Event or
Admin limit. Dynamic routes remain behind `VITE_EVENTS_LAUNCH_ENABLED`, which is OFF in Production.
The five-poster static carousel therefore remains the live UI, and Event launch still requires
separate approval.

Verification at this continuation point:

- isolated local API acceptance completed 79 assertions and real browser acceptance passed Admin
  edit, signed cover, slider retry, detail/deep-link EN/DE, desktop/mobile and empty-state paths;
- frontend full suite 84 files / 774 tests PASS; TypeScript, ESLint, Prettier and normal plus
  launch-mode production builds PASS; launch-mode JS has no hardcoded static Event record titles;
- backend focused Event suite 121/121 PASS; Ruff and strict mypy PASS; Alembic reports one head at
  `0021_restore_runtime_permissions`;
- backend full suite on the repository-supported Python 3.12 runtime: 1,408 PASS, 37 SKIP. The two
  former Chat WebSocket failures were a cross-loop fake transport and asynchronous teardown race;
  the test harness now uses the TestClient portal and deterministic cleanup. Application WebSocket
  code is unchanged, and `EVS-007` is DONE;
- local acceptance discovered and covered async `updated_at` projection, Event-detail session
  bootstrap, live empty-state and phase-boundary consistency regressions; Quality Gate E is PASS;
- Production preflight proved the live baseline, Alembic head `0021`, private `event-media` bucket,
  skew compatibility and executable Vercel/Render rollback;
- `origin/main` reached `e2ef4c0`; GitHub CI Backend/Frontend succeeded, Vercel deployment
  `dpl_Evhx9hudQSBf99P9fxznxtGNg2GS` is READY and Render deploy
  `dep-db4v9lqvcj2c73e5jvlg` is LIVE at the same application SHA;
- safe Production smoke passed live/readiness, canonical empty Event reads, static desktop/mobile
  carousel, existing USER Profile/Matching reads and zero browser warning/error. No Event/account/
  Storage/database write, seed, publish, flag, secret or provider-setting change occurred.

The signed evidence is in
`docs/operations/accept-event-001-local-acceptance-2026-10-10.md` and
`docs/operations/accept-event-001-production-release-2026-10-10.md`. Do not rerun Local A–E,
Quality Gate E or the flag-OFF smoke without a regression reason. The next Event action is owner
content/launch approval, not another code deployment.

The owner superseded the cloud-Staging prerequisite on 2026-10-09. Because Upstash Free provides one
database and it is Production-only, the approved Event path is isolated local A–E, Production
preflight with executable Vercel/Render rollback, controlled `main` deployment while the Event flag
remains OFF, and safe Production smoke. Do not use Production dependencies for local acceptance.
Production write tests, canonical Event data mutation/publish and enabling the Event flag remain
unauthorized. Distinguish Local PASS, Production Smoke PASS and NOT RUN evidence.

Previously, the owner separately authorized `FE-LANDING-BG-001`, followed by
`FE-PROFILE-HOME-UNI-001`, on local `main`; both are now deployed from commit `2f6f8c8` with
automated checks passing.
Read `docs/implementation/phase-2-roadmap.md` and only those two task extracts plus their named
source/tests. Direct Production desktop/mobile/transition verification closes the Landing task.
Authenticated Profile display/edit/save/reload remains a manual gate because no account was used
during release verification. Do not mark that gate PASS without direct evidence. Do not retry
Semester Prepare, mutate a
provider or rerun accepted functional/technical paths. The release lane remains documented in
`docs/implementation/tasks/PROD-001.md`,
`docs/operations/prod-001-technical-evidence-2026-10-08.md`,
`docs/implementation/production-status.md` and
`docs/implementation/post-deployment-workflow.md` unless an owner separately authorizes one of the
blocked remediation steps.

The 2026-10-10 Event code-deployment approval was consumed by the `e2ef4c0` push and controlled
Vercel/Render rollout. It did not and does not authorize Production Event writes, migration changes,
provider/secret changes, Event publication or enabling the Event flag.

Final continuation verification is complete. Repository HEAD and `origin/main` are the docs-only
commit `e0ef343`; GitHub Actions run `38038014039` completed Backend/Frontend SUCCESS. Vercel
deployment `dpl_3ndKHjjd57dNtye1X1k3Sw2Pd5HY` is READY and still serves accepted application bundle
`index-phrHnhsS.js`. Render did not deploy the docs-only commit and remains LIVE at application SHA
`e2ef4c0` with prior `d15cb1d` retained for Rollback. Public site/live/readiness are 200, the five
static posters remain in the bundle, the launch flag remains OFF, and a direct read-only database
count confirms zero canonical Event rows.

One architecture decision is now required before Production data preparation. The only current
launch flag, `VITE_EVENTS_LAUNCH_ENABLED`, couples the Landing live slider and most public/User/Admin
Event surfaces. Admin create/edit child routes are registered behind ADMIN RBAC outside that flag,
but list/navigation are hidden, so this is not a supported Admin-only rollout. Preferred Phase A
requires a separately approved frontend change that splits Admin management from public-live
activation and consistently gates list/create/edit/navigation/metrics. Do not use direct URLs as a
workaround, do not change the existing flag, and do not create Event data without fresh approval.

## Latest Event code release

- Production preflight and rollback: PASS. After the docs-only deployment, Vercel marks the
  accepted `e2ef4c0` deployment as the native rollback candidate; pre-Event `253849d`/`c2fbaf1`
  deployments remain READY and can be explicitly promoted. Render exposes native rollback from the
  live `e2ef4c0` deploy to prior `d15cb1d`. No migration was added, so code rollback requires no
  database downgrade.
- GitHub Actions run `38037425291`: Backend SUCCESS; Frontend SUCCESS.
- Vercel: `dpl_Evhx9hudQSBf99P9fxznxtGNg2GS` READY at `e2ef4c0`.
- Render: `dep-db4v9lqvcj2c73e5jvlg` LIVE at `e2ef4c0`.
- Public API: live/ready 200; anonymous auth 401/no-store; slider 200 `[]`; Event list 200 with total
  zero; nonexistent detail 404; anonymous Admin Event list 401/no-store.
- Production bundle `index-phrHnhsS.js` contains all five static titles and no canonical slider or
  Admin Event API marker. Desktop/mobile Landing, protected Profile and Buddy Matching reads passed
  with zero browser warning/error. Admin Event UI and Event Detail UI are intentionally NOT RUN in
  Production because the flag is OFF and canonical Event total is zero.

## Latest Phase 2 frontend release

- Landing corrective source commit `c2fbaf1f1082c6bb5d790d32add3b603f3b251fe` reached
  `origin/main`; Vercel Production deployment `6952736000`, Frontend and Backend checks succeeded.
- `www.vgubuddyprogram.com` served `index-CC-xLBAH.js`. Direct Brave verification completed 15
  desktop transitions/three full loops plus mobile, hard-reload and reduced-motion checks with no
  blank/undecoded/visible-source-change sample, layout delta, overflow or console issue.
- The earlier feature release used `2f6f8c8cb4bd15fb4ece1821e8cfc1b4ac3ea8f7`; GitHub recorded
  Vercel Production deployment `6951736865` successful and both repository checks passed.
- `www.vgubuddyprogram.com` returned 200 and served `index-Deo6vyVU.js` with all five Landing asset
  markers, EN/DE Home University copy and the first-party API target.
- Brave visual verification passed at desktop 1536x831 and mobile 390x844, including image decode,
  responsive navigation, no overflow, Welcome-card absence and the live opacity crossfade.
- Public API live/readiness remained 200; anonymous `/auth/me` remained 401/no-store with the exact
  first-party CORS origin.
- The release verification used no account. A later owner observation confirmed Home University
  display; edit/save/reload/clear/max-length acceptance remains open.

## Latest verified Production snapshot

Authenticated and provider-dashboard checks at 2026-10-08 14:15–15:01 Asia/Saigon established:

- Secure/HttpOnly/SameSite=Lax/API-host-only `__Host-` access, refresh and CSRF cookies;
- USER session reload recovery and logout invalidation with all three cookie names removed;
- authenticated notification/conversation WSS 101 using the exact first-party Origin, plus reload
  reconnection and REST history recovery without a test message;
- ADMIN Semester management GET 200 and a working `NEW_COHORT` restore guard;
- a real failed Semester preparation: operation `RESET_PREPARATION_FAILED`, private backup `FAILED`
  and unverified, with two retained earlier Prepare responses of 503;
- Vercel current deployment `dpl_FZAGsVudHtTiWkomWHBbV7J5k6MB` plus prior Ready candidates;
- Render service `srv-db343ne7bikc73bjv910`, deploy `dep-db343nu7bikc73bjvalg`, application commit
  `d15cb1d7`, and only one available deploy;
- no Render events in the preceding 12 hours, no `ERROR` log match in the preceding hour and
  repeated 200 live probes.

That one-deploy Render observation is historical. The 2026-10-10 Event release now retains live
`e2ef4c0` plus prior `d15cb1d` with a native rollback action, as recorded above.

Both USER and ADMIN sessions were logged out. No credential/token/cookie value or private payload
was recorded. Opening the existing chat may have reconciled its ordinary idempotent read marker; no
message or Buddy relationship was created, changed or deleted.

Read-only checks at 2026-10-08 10:27 Asia/Saigon established:

- `api.vgubuddyprogram.com` CNAMEs to `vgu-buddy-api-production.onrender.com`;
- `www.vgubuddyprogram.com` CNAMEs to `3d95265b44dec908.vercel-dns-017.com`;
- `GET /api/health/live` returned 200 with `{"status":"alive"}`;
- `GET /api/health/ready` returned 200 with database and Redis `ok`, email and Storage
  `configured`;
- the deployed frontend bundle contains `https://api.vgubuddyprogram.com/api`;
- unauthenticated `GET /api/auth/me` returned 401 with `Cache-Control: no-store`;
- first-party login preflight from `https://www.vgubuddyprogram.com` returned 200 with credentialed
  exact-origin CORS; an unrelated origin returned 400.
- the deployed `/assets/index-DIl7WhwA.js` bundle contained all five current static Event titles
  from the committed carousel update (`Recruitment`, `Club Fair 26`, `Experience Day`, `Christmas`,
  `Halloween`).

Therefore DNS cutover and public dependency readiness are PASS. Older records saying DNS is pending
are superseded. These checks do not by themselves prove cookie/session recovery, CSRF negative
behavior, protocol-level authenticated WebSocket behavior, Semester safeguards or release hold and
rollback readiness.

## Owner Manual Acceptance — PASS

On 2026-10-08, the owner explicitly confirmed successful first-party Production use with no
functional errors for:

- Admin login and Dashboard;
- User login and Dashboard;
- Buddy Recommendation;
- Invitations and Accept Invitation;
- Buddy Matching;
- Chat and related features.

This is trusted dated functional evidence. Do not ask the owner to repeat these paths merely to
produce another record. It does not replace the technical/security and operational gates below.

## Preserve these verified gates

- Production Upstash reallocation/credential rotation: PASS.
- Supabase Production project, zero-to-head migration and runtime role: PASS at Alembic head
  `0021_restore_runtime_permissions`.
- Production email Edge worker, Cron path, one fresh delivered verification message and normal user
  verification flow: documented PASS.
- Restore-blocked-after-new-USER acceptance: PASS/CLOSED.
- Public DNS, live/readiness, frontend API target, anonymous auth boundary and basic CORS: PASS as
  above.
- Owner-confirmed Admin/User dashboards and Recommendation -> Invitation -> Accept -> Match -> Chat
  functional smoke: PASS on 2026-10-08.
- Release-candidate automated baseline: web 721 tests and API 1,330 tests on the documented baseline.
  HEAD later added the committed static-event asset/title update `81979ce`; its expected five titles
  are present in the deployed bundle, but the older full-suite count alone is not new automated-test
  evidence for that delta.
- Focused technical verification: 60 web tests and 143 API tests PASS.
- Secure cookies, session reload/logout, CSRF coverage, authenticated WSS Origin/auth/reconnect,
  REST recovery, Semester authorization/guards and the high-confidence secret/history scan: PASS.
- Vercel retained frontend rollback candidates: PASS.
- Render retained backend rollback candidate: PASS from the 2026-10-10 Event code rollout.

## Blocking `PROD-001`

- Private Semester-backup access is **FAIL** in direct Production evidence. A separate owner-approved
  remediation and safe verification are required; Prepare is state-changing and was not retried.
- Supply the named rollback decision owner, Vercel executor, Render executor and database-recovery
  owner. Do not infer names.
- Supply the accepted post-repair hold duration, then observe only that missing interval.
- Residual `ACCEPT-001` evidence and full encrypted off-site DR restore remain post-deployment
  hardening, not completed work.
- Dynamic Event/Admin Event code is deployed and remains feature-gated OFF pending separate
  canonical data preparation and Event launch approval.

## Phase 2 readiness

- Planning is READY.
- `FE-LANDING-BG-001` is DONE / PRODUCTION VERIFIED.
- `FE-PROFILE-HOME-UNI-001` is DEPLOYED; authenticated display is owner-accepted while
  edit/save/reload/clear/max-length acceptance remains open.
- Events, Event Calendar, VGU Map, AI Assistant, Merchandise and remaining enhancements follow in
  that owner-approved order, subject to their own dependencies and a separate instruction.
- Backup/DR, `PROD-001`, `SEM-008` and residual `ACCEPT-001` remain open; this does not make Phase 1
  release-ready.
- Reuse this record's Production session/WSS/recovery evidence in `ACCEPT-001`; do not repeat it.

## Worktree boundary

The documentation optimization commit `c62b055` was pushed to `origin/main`. It intentionally
incorporated the pre-existing uncommitted documentation changes in `README.md`, the legacy plan and
operations records. The follow-up acceptance synchronization is documentation-only. No application
source, database, provider resource or Production state was changed by either documentation pass.

The PROD-001 technical-closure documentation is a separate docs-only change. Its resulting commit
and push status must be recorded after validation; do not alter the legacy archive.
