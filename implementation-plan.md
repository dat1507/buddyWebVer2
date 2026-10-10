# BuddyWebv2 lightweight implementation plan

**Plan version:** 1.11
**Updated:** 2026-10-11
**Legacy archive:** `implementation_plan_vgu_buddy.md`
**Task registry:** `docs/implementation/task-index.md`
**Phase 2 roadmap:** `docs/implementation/phase-2-roadmap.md`

This file is the control plane for current status and execution order. It deliberately excludes
long-form completed-session evidence and repeated architecture prose. Every preserved Task ID has a
focused extract under `docs/implementation/tasks/`.

## Current release state

The progress-reporting MVP is deployed behind first-party DNS. Public read-only checks confirm that
the Vercel frontend points to the first-party Render API and that live/readiness, dependency status,
anonymous auth caching and exact-origin CORS behave as expected. This supersedes the older plan text
that described DNS cutover as pending.

On 2026-10-08 the owner confirmed **PASS** with no functional errors for Admin login/Dashboard, User
login/Dashboard, Buddy Recommendation, Invitations, Accept Invitation, Buddy Matching, Chat and
related features. Reuse that functional evidence; do not rerun those paths merely for documentation.

`PROD-001` is **BLOCKED / OWNER ACTION REQUIRED**, not DONE. Session/cookie/CSRF, authenticated WSS,
REST recovery, Semester guards and focused release-security verification now pass. Direct
Production evidence found a failed, unverified private Semester backup; named rollback/recovery
owners and the accepted post-repair hold duration are also missing. The Event code release on
2026-10-10 created a retained Render rollback point, closing that one earlier blocker without
closing `PROD-001`. No application feature should be implemented in this release lane. A newer owner
decision separately authorizes the two isolated frontend-only Phase 2 tasks below on local `main`;
the owner subsequently approved and completed their `origin/main` push and Vercel Production
deployment on 2026-10-09. This does not change any Phase 1 blocker.

The owner later confirmed that the corrected Landing slideshow is smooth in Production and that
Home University displays correctly in the authenticated Profile UI. This preserves both Landing
tasks as DONE and closes only the Profile display gate; edit/save/reload/clear/max-length acceptance
remains open under the original Profile contract.

## Executable status

| Order | Task / gate                     | Priority           | Status                                                           | Dependency / reason                                                                                                                                               | Next evidence                                                                                     |
| ----- | ------------------------------- | ------------------ | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 1     | `PROD-001`                      | Release-blocking   | **BLOCKED / OWNER ACTION REQUIRED**                              | Private Semester backup failed; named owners and accepted post-repair hold remain missing; Render rollback is now retained                                        | Separately authorize backup remediation/verification, name owners and accept the post-repair hold |
| 2     | `ACCEPT-001` residual evidence  | High hardening     | **OPEN / POST-DEPLOY**                                           | Smaller MVP release boundary approved; integrity guards already exist                                                                                             | Close only missing signed/redacted evidence; do not rerun accepted scenarios                      |
| 3     | Encrypted off-site DR rehearsal | High hardening     | **OPEN / POST-DEPLOY**                                           | Production exists; DR roles/runbook prepared                                                                                                                      | Full encrypted snapshot plus disposable restore evidence                                          |
| 4     | `EVS-007` Event regression gate | P0 product         | **DONE — SUPPORTED-RUNTIME REGRESSION PASS**                     | Current regression: Python 3.12 backend 1,408 PASS / 37 SKIP; Event backend 121 PASS; frontend 774 PASS                                                           | Preserve evidence; no repeat without regression reason                                            |
| 5     | `ACCEPT-EVENT-001`              | P0 release gate    | **DONE — FLAG-OFF RELEASE VERIFIED / PRODUCTION WRITES NOT RUN** | Local A–E, Quality Gate E, rollback preflight, controlled deploy and read-only smoke passed at `e2ef4c0`; Production create/edit/upload intentionally remain open | Preserve evidence; decide Admin/public flag split before canonical data and launch approval       |
| 6     | `EVENT-FLAG-SPLIT`              | P0 product-release | **RELEASE CANDIDATE — LOCAL GATES PASS / BOTH PROD FLAGS OFF**   | Independent strict flags, route consistency and six matrix configurations pass; Production keys are absent                                                        | Controlled `main` rollout and read-only OFF/OFF smoke; stop before Admin activation               |
| 7     | P1 product backlog              | P1                 | **PLANNED**                                                      | Depends on task-specific contracts                                                                                                                                | Select explicitly after P0 post-deployment sequence                                               |
| 8     | `FE-LANDING-BG-001`             | Phase 2 Priority 1 | **DONE — PRODUCTION VERIFIED**                                   | Vercel Production and desktop/mobile/transition evidence pass                                                                                                     | Preserve evidence; no repeat without regression reason                                            |
| 9     | `FE-PROFILE-HOME-UNI-001`       | Phase 2 Priority 2 | **DEPLOYED — DISPLAY ACCEPTED / EDIT-PERSISTENCE GATES OPEN**    | Owner confirmed correct Production display; automated behavior tests pass                                                                                         | Owner edit/save/reload/clear/max-length review                                                    |
| 10    | `FE-LANDING-BG-002`             | Phase 2 corrective | **DONE — PRODUCTION VERIFIED**                                   | `c2fbaf1`; Vercel deployment `6952736000`; 15-transition Production audit pass                                                                                    | Preserve evidence; no repeat without regression reason                                            |

`SESSION_HANDOFF.md` records the Phase 2 frontend deployment and remaining authenticated Profile
visual gate. `PROD-001`, Backup/DR, `SEM-008` and `ACCEPT-001` remain open in the release lane. The
completed frontend release does not authorize database or other provider mutation.

The owner separately authorized `FE-LANDING-BG-002` as a corrective Landing-only implementation,
push and Vercel deployment. That release is complete and its authorization is consumed; it does
not authorize any other feature or Production mutation.

The owner authorized `EVENT-FLAG-SPLIT` on 2026-10-11. Local implementation and all frontend gates
pass. The release changes only build-time frontend controls: exact `true` on
`VITE_ADMIN_EVENTS_ENABLED` or `VITE_PUBLIC_EVENTS_ENABLED` enables its own surface; missing or
invalid values remain OFF, and the legacy shared key is ignored. Both Production keys are absent.
The authorized rollout must therefore preserve the static five-poster Landing and hidden Admin/
public Event surfaces, then stop at the separate Admin-only activation approval gate.

## Completed release gates — do not repeat without a regression reason

- Upstash Production-only reallocation and credential rotation.
- Supabase Production project bootstrap, runtime credential and zero-to-head migration at `0021`.
- Production email-worker deployment, secrets/Vault/Cron path, delivered verification email and
  normal user verification.
- Restore-blocked-after-new-USER guard.
- First-party API and `www` DNS cutover.
- Public `/live` and dependency-aware `/ready` checks.
- Deployed bundle first-party API target, anonymous `/auth/me` 401/no-store and positive/negative
  CORS preflight.
- Owner-confirmed Admin/User dashboards and Recommendation -> Invitation -> Accept -> Match -> Chat
  functional smoke on 2026-10-08.

## `PROD-001` remaining execution order

These are evidence stages inside the existing Task ID; they are not new feature Task IDs.

1. Preserve the now-PASS cookie/session/CSRF, WSS/reconnect/REST, Semester-guard, secret-scan and
   frontend rollback evidence; do not repeat it without a regression reason.
2. Obtain separate authorization to diagnose and repair the failed private Semester-backup
   connection/storage path. Its eventual verification is state-changing and is not authorized by
   this evidence task.
3. Preserve the schema-compatible Render rollback now retained from `e2ef4c0` to `d15cb1d`.
4. Record named rollback decision, Vercel execution, Render execution and database-recovery owners;
   then observe only the additional owner-approved post-repair hold window.
5. Close `PROD-001` only when those blockers pass. Detailed evidence is in
   `docs/operations/prod-001-technical-evidence-2026-10-08.md`.

Detailed safe execution and stop conditions are in
`docs/implementation/post-deployment-workflow.md`.

## Post-deployment hardening order

1. Finish only the missing `ACCEPT-001` evidence: maximum invitation boundaries/inert rendering,
   stale-tab type-lock UX and Accept-vs-update race, multiple-Buddy/chat retention, Admin
   reconciliation, and consolidated signed/redacted record. The restore-blocked scenario is already
   PASS and must not be repeated merely for documentation.
2. Produce one encrypted off-site snapshot and one disposable full restore rehearsal using the
   dedicated DR role and documented runbook.
3. Prove physical expired-message cleanup/retention evidence and scheduled maintenance health.
4. Observe Render cold start, Free-hour consumption and error/reconnect behavior; reevaluate paid
   capacity only from measured failure or sustained operational need.
5. Finish the broader accessibility/candidate matrix and low-risk tooling/performance items.

## Dynamic Event lane — exact order and current state

After release hold/hardening selection, preserve this controlling Part 27 sequence:

`EVT-005 -> EVT-006 -> EVT-009 -> EVT-011 -> EVS-005 -> ADMIN-006 -> ADMIN-007 ->`
`ADMIN-008 -> ADMIN-009 -> FE-031 -> FE-014B -> EVS-007 -> ACCEPT-EVENT-001`

On 2026-10-09 the owner selected this lane. `EVT-005/006/009/011`, `EVS-005`, `ADMIN-006..009`,
`FE-031` and `FE-014B` are implemented and deployed behind the OFF launch flag with focused
automated gates passing. The canonical
source is one Event model: the Landing slider is a derived PUBLIC/PUBLISHED/upcoming projection;
there is no standalone slider table, manual ordering page or duplicated promotion CRUD.

`EVS-007` is DONE. The current post-acceptance regression is 1,408 backend PASS / 37 SKIP on the
project's Python 3.12 runtime, 121 focused Event PASS and 84 files / 774 frontend PASS. Ruff, strict
mypy, TypeScript, ESLint, Prettier, normal/launch builds and dependency audits pass. Landing renders
the first five canonical results while the server's 12-row bounded API cap remains unchanged.

The owner superseded the cloud-Staging prerequisite on 2026-10-09 because Upstash Free provides one
database and it is reserved for Production. `ACCEPT-EVENT-001` now executes as isolated local A–E,
then Production preflight with executable Vercel and Render rollback, controlled `main` deployment
with `VITE_EVENTS_LAUNCH_ENABLED` still OFF, and safe read-only/non-destructive Production smoke.
This changes the environment, not the security or quality criteria. Production write tests remain
separately unauthorized, and enabling the Event flag still requires explicit launch approval.

On 2026-10-10 isolated local A–E and Quality Gate E completed **PASS**. The API harness recorded 79
assertions; real browser acceptance covered Admin edit, signed cover, retry, detail/deep-link EN/DE,
responsive layout and empty state with zero runtime or console errors. Four acceptance regressions
have focused coverage: async `updated_at` projection, detail query/session bootstrap, live empty
state and a phase-boundary projection race.

Production preflight then proved Alembic `0021`, private Event Storage, current frontend/backend
baselines, skew compatibility and executable rollback. `e2ef4c0` reached Vercel and Render; GitHub
Backend/Frontend CI succeeded. Flag-OFF read-only smoke passed health/readiness, empty canonical
Event reads, the static desktop/mobile carousel, existing USER Profile/Matching reads and browser
console sanity. The docs-only `e0ef343` follow-up also passed both CI jobs; Vercel remained READY
with the same accepted bundle, and Render correctly stayed on backend SHA `e2ef4c0`.

Current Event evidence classification:

- `EVS-007`: **DONE — VERIFIED** on the supported runtime.
- `EVT-005/006/009/011`, `EVS-005`, `ADMIN-006..009`, `FE-031` and `FE-014B`: implementation is
  deployed and **DONE — LOCAL VERIFIED** under the owner-approved isolated replacement gate; this
  does not assert Production create/edit/upload or flag-ON rendering.
- `ACCEPT-EVENT-001`: **DONE — FLAG-OFF RELEASE VERIFIED**. Its local mutation acceptance and
  Production read-only smoke are complete; the Production write portion is explicitly **OPEN —
  NEEDS PRODUCTION WRITE ACCEPTANCE**.
- Admin activation architecture and canonical data preparation are **OPEN — AWAITING ADMIN EVENT
  APPROVAL**. Public Live Slider activation is separately **OPEN — AWAITING EVENT LAUNCH APPROVAL**.
- `FE-PROFILE-HOME-UNI-001` remains deployed with display accepted; edit/save/reload,
  clear-to-null and max-length acceptance remain open.

The current single `VITE_EVENTS_LAUNCH_ENABLED` build flag cannot support the preferred Admin-ON /
Public-OFF sequence: it controls the Landing live slider plus most public/User/Admin Event surfaces.
Admin create/edit child routes are registered outside that condition but remain ADMIN-protected and
are not a supported management path while list/navigation are hidden. A separately approved small
frontend task must split Admin management from public-live activation and gate all Admin Event
routes consistently before Phase A. No refactor or activation is authorized by this plan update.

The current static carousel does not complete any dynamic Event task.

## P1 and research backlog

The following remain non-release-critical and require explicit selection:

- Owner-approved Phase 2 order after the two current UI tasks: Event system -> Event Calendar ->
  VGU Map -> AI Assistant -> Merchandise -> remaining enhancements.

- `AUTH-025 -> FE-024` — authenticated password change and real Settings actions.
- `EVT-007 -> ADMIN-011/FE-032` — event registration API, Admin detail and User action.
- `ADMIN-EVT-002` — recap gallery upload/ordering after its recap/media prerequisites.
- `FE-030`, then `FE-EVENT-CALENDAR-001` after stable Event APIs and live integration.
- `FE-036` only after the V2 feedback contract is reconfirmed.
- `MATCH-005`, `MATCH-006` research comparisons only; they do not drive V2 recommendations.
- RAG, campus, notifications, analytics and portfolio tracks require unique Task IDs and complete
  contracts before implementation.

## Superseded work — never execute from old contracts

- Old 1:1 assignment/publication lane: `MATCH-001/003/004/007/008/009/010/013/014`,
  `FE-033/034/035/037`, and `ADMIN-014/015/016/017` are superseded by the completed V2
  recommendation/invitation/current-Buddy architecture where noted in their extracts.
- Old Admin Slider-specific UI (`ADMIN-SLIDER-001..004`) and duplicated EventSlider assumptions are
  superseded by the controlling canonical Event plan in Part 27.
- Ambiguous future shorthand such as `ADMIN-019..027` has no executable contract and must be
  recontracted.

## Documentation routing

- Current handoff: `SESSION_HANDOFF.md`
- Production truth: `docs/implementation/production-status.md`
- Post-deployment workflow: `docs/implementation/post-deployment-workflow.md`
- Phase 2 roadmap: `docs/implementation/phase-2-roadmap.md`
- Technical decisions: `docs/implementation/decision-log.md`
- Important completion history: `docs/implementation/history.md`
- All Task IDs and focused extracts: `docs/implementation/task-index.md`
- Migration/validation evidence: `docs/implementation/validation.md`
- Full legacy record: `implementation_plan_vgu_buddy.md` (archive only)

## Status update rule

A task becomes DONE only when its acceptance criteria and relevant automated/manual gates have dated
evidence. Implementation without acceptance remains IN PROGRESS. A plan statement does not prove a
runtime state; Production claims require dated direct or operator evidence. Update this file and the
handoff together after any status transition.
