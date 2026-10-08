# BuddyWebv2 lightweight implementation plan

**Plan version:** 1.2
**Updated:** 2026-10-08
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
Production evidence found a failed, unverified private Semester backup; Render has no previous
retained backend deploy; named rollback/recovery owners and the accepted post-repair hold duration
are also missing. No application feature should be implemented in this release lane. A newer owner
decision separately authorizes the two isolated frontend-only Phase 2 tasks below on local `main`;
it does not authorize a push/deployment or change any Phase 1 blocker.

## Executable status

| Order | Task / gate | Priority | Status | Dependency / reason | Next evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | `PROD-001` | Release-blocking | **BLOCKED / OWNER ACTION REQUIRED** | Private Semester backup failed; no retained Render rollback point or named owners | Separately authorize backup remediation/verification, establish backend rollback, name owners and accept the post-repair hold |
| 2 | `ACCEPT-001` residual evidence | High hardening | **OPEN / POST-DEPLOY** | Smaller MVP release boundary approved; integrity guards already exist | Close only missing signed/redacted evidence; do not rerun accepted scenarios |
| 3 | Encrypted off-site DR rehearsal | High hardening | **OPEN / POST-DEPLOY** | Production exists; DR roles/runbook prepared | Full encrypted snapshot plus disposable restore evidence |
| 4 | `EVT-005` dynamic Event lane | P0 product backlog | **DEFERRED / READY AFTER RELEASE HOLD** | Existing Event model/service prerequisites are complete | Start exact Part 27 chain only after release/hardening decision |
| 5 | P1 product backlog | P1 | **PLANNED** | Depends on task-specific contracts | Select explicitly after P0 post-deployment sequence |
| 6 | `FE-LANDING-BG-001` | Phase 2 Priority 1 | **IMPLEMENTED — AUTOMATED PASS / VISUAL GATE OPEN** | Local source/assets complete; browser surfaces could not reach the local Vite server | Owner desktop/mobile/transition review; stop before push/deploy |
| 7 | `FE-PROFILE-HOME-UNI-001` | Phase 2 Priority 2 | **IMPLEMENTED — AUTOMATED PASS / VISUAL GATE OPEN** | Existing Profile API field reused; no backend/matching change | Owner authenticated Profile display/edit/reload review; stop before push/deploy |

`SESSION_HANDOFF.md` records the bounded Phase 2 frontend implementation and remaining manual visual
gate. `PROD-001`, Backup/DR, `SEM-008` and `ACCEPT-001` remain open in the release lane. Local
implementation does not authorize database, provider or Production mutation.

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
3. Establish one schema-compatible retained Render deploy or an approved immutable redeploy path
   for the current backend revision.
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
