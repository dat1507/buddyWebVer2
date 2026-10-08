# BuddyWebv2 lightweight implementation plan

**Plan version:** 1.0
**Updated:** 2026-10-08
**Legacy archive:** `implementation_plan_vgu_buddy.md`
**Task registry:** `docs/implementation/task-index.md`

This file is the control plane for current status and execution order. It deliberately excludes
long-form completed-session evidence and repeated architecture prose. Every preserved Task ID has a
focused extract under `docs/implementation/tasks/`.

## Current release state

The progress-reporting MVP is deployed behind first-party DNS. Public read-only checks confirm that
the Vercel frontend points to the first-party Render API and that live/readiness, dependency status,
anonymous auth caching and exact-origin CORS behave as expected. This supersedes the older plan text
that described DNS cutover as pending.

`PROD-001` remains **IN PROGRESS**, not DONE. Public infrastructure checks have passed, while the
authenticated production smoke/hold evidence below is still incomplete. No new application feature
is needed to continue this release lane.

## Executable status

| Order | Task / gate | Priority | Status | Dependency / reason | Next evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | `PROD-001` | Release-blocking | **IN PROGRESS / READY** | Production is deployed; DNS and public readiness pass | Authenticated Admin/session/core Buddy/WSS/Semester-guard smoke, hold and rollback record |
| 2 | `ACCEPT-001` residual evidence | High hardening | **OPEN / POST-DEPLOY** | Smaller MVP release boundary approved; integrity guards already exist | Close only missing signed/redacted evidence; do not rerun accepted scenarios |
| 3 | Encrypted off-site DR rehearsal | High hardening | **OPEN / POST-DEPLOY** | Production exists; DR roles/runbook prepared | Full encrypted snapshot plus disposable restore evidence |
| 4 | `EVT-005` dynamic Event lane | P0 product backlog | **DEFERRED / READY AFTER RELEASE HOLD** | Existing Event model/service prerequisites are complete | Start exact Part 27 chain only after release/hardening decision |
| 5 | P1 product backlog | P1 | **PLANNED** | Depends on task-specific contracts | Select explicitly after P0 post-deployment sequence |

No task is assigned in `SESSION_HANDOFF.md`; report this table and wait for the user's selection.

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

## `PROD-001` remaining execution order

These are evidence stages inside the existing Task ID; they are not new feature Task IDs.

1. **Authenticated Admin smoke:** login through the deployed UI, direct-refresh protected Admin
   routes, safe monitoring/user detail reads, logout and denied re-entry.
2. **Second designated USER:** provision through the normal registration/email-verification flow;
   do not create a synthetic relationship or edit verification state.
3. **Core Buddy lifecycle:** complete two opposite-type profiles, Recommendations, invitation send
   and email, recipient Accept, active Current Buddy, chat history/send/receive/read/reload and safe
   participant boundaries.
4. **First-party session/security smoke:** Secure host-only cookies, refresh/session recovery, CSRF,
   rejected foreign origin, WSS origin/auth/reconnect and no private-cache leakage after logout.
5. **Non-destructive Semester guard:** read-only/status UI and guard behavior only; do not perform a
   destructive Production reset/restore for deployment proof.
6. **Hold/rollback evidence:** observe health/error/job/WSS signals through the agreed hold period,
   record retained Render/Vercel rollback points and responsible owner.
7. Close `PROD-001` only after every applicable production acceptance item is evidenced. A public
   200 health response alone cannot close it.

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

## Deferred dynamic Event lane — exact order

After release hold/hardening selection, preserve this controlling Part 27 sequence:

`EVT-005 -> EVT-006 -> EVT-009 -> EVT-011 -> EVS-005 -> ADMIN-006 -> ADMIN-007 ->`
`ADMIN-008 -> ADMIN-009 -> FE-031 -> FE-014B -> EVS-007 -> ACCEPT-EVENT-001`

Manual gates:

- API/RBAC/query acceptance after `EVT-006`.
- Storage ownership/readiness and replacement cleanup after `EVT-011`.
- Admin create/publish/public-visibility acceptance after `ADMIN-009`.
- Landing/detail freshness and cache acceptance after `FE-014B`.
- Full real Admin/public staging acceptance at `ACCEPT-EVENT-001` before enabling the dynamic flag.

The current static carousel does not complete any dynamic Event task.

## P1 and research backlog

The following remain non-release-critical and require explicit selection:

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
