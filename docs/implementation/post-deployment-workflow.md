# Post-deployment workflow

This workflow is evidence-only unless the user separately authorizes Production interaction. It does
not authorize account creation, login, email sends, DNS/provider changes or destructive operations.

**Current Stage 1 checkpoint — 2026-10-10:** session/cookie/CSRF, authenticated WSS/reconnect/REST,
Semester guards, focused release-security evidence and retained Vercel/Render code rollback are
PASS. Stage 1 remains BLOCKED by the failed private Semester backup, unnamed rollback/recovery
owners and unaccepted post-repair hold duration. Preserve the earlier PASS evidence in
`../operations/prod-001-technical-evidence-2026-10-08.md`; do not repeat it during remediation.

## Stage 1 — Close `PROD-001`

Owner functional acceptance is PASS on 2026-10-08 for Admin login/Dashboard, User login/Dashboard,
Buddy Recommendation, Invitations, Accept Invitation, Buddy Matching, Chat and related features.
Do not repeat those paths solely for documentation. Stage 1 now collects only the technical,
security and operational evidence not established by that acceptance.

### 1. Preserve the deployed baseline

- Record current Git SHA, Vercel deployment and Render deployment/rollback point.
- Confirm `/live` and `/ready`; do not rerun migrations when Alembic is already at head.
- Confirm monitoring owners and a rollback decision channel before authenticated smoke.

### 2. First-party session/security evidence

- Inspect Secure HttpOnly host-only cookie attributes and session refresh/recovery without recording
  credential or cookie values.
- Record CSRF success and rejected negative path; reuse the already-PASS exact-origin CORS evidence.
- Verify private cache removal after logout/account change only if it is not already covered by the
  owner's accepted functional session. Stop on role leakage, stale private data or unexpected
  mutation controls.

### 3. Protocol-level realtime evidence

- Prove authenticated WSS Origin/auth handling, reconnect and REST history recovery with sanitized
  transport evidence.
- Do not infer these protocol properties from the owner's functional Chat PASS alone and do not
  recreate chat data merely for screenshots.

### 4. Release safety evidence

- Verify non-destructive Semester status/guard behavior; never execute Production Reset/Restore for
  deployment proof.
- Record the final secret/history scan, credential-rotation status, private-backup access controls
  and destructive-control review without exposing a secret or private payload.

### 5. Hold and rollback gate

- Observe health, error rate, email/Cron/outbox, Redis and WSS signals for the agreed period.
- Confirm named rollback/recovery owners and that retained frontend/API deployments remain compatible
  with database head `0021`.
- Close `PROD-001` only with dated redacted evidence. Do not run Production Semester Reset/Restore.

### 6. Current owner-action sequence

1. Open a separately authorized remediation task for the failed private Semester-backup path. Do
   not invoke Prepare merely as a diagnostic from a documentation/evidence task.
2. Preserve the retained Render `e2ef4c0` -> `d15cb1d` code rollback established on 2026-10-10.
3. Record the named rollback decision, Vercel, Render and database-recovery owners.
4. Record the accepted post-repair hold duration, observe only the missing window, then reconcile
   `PROD-001` again.

## Stage 2 — Residual hardening

1. Close only missing `ACCEPT-001` cases. Reuse all accepted evidence.
2. Execute encrypted off-site backup plus disposable full restore through the DR runbook.
3. Capture expired-message physical cleanup and maintenance scheduling evidence.
4. Measure cold-start, Free-hour, reconnect and load behavior; do not authorize paid changes from
   documentation alone.
5. Finish the broader accessibility and candidate matrix.

## Stage 3 — Dynamic Event/Admin Event track

Run only after an explicit post-deployment product decision:

1. `EVT-005` — public Event list/detail queries.
2. `EVT-006` — Admin Event list/detail/CRUD/status API.
3. `EVT-009` — audit and freshness integration.
4. `EVT-011` — poster lifecycle and Storage readiness.
5. `EVS-005` — public Event-derived slider endpoint.
6. `ADMIN-006` — Admin Event list.
7. `ADMIN-007` — create form/poster upload.
8. `ADMIN-008` — edit/poster replacement.
9. `ADMIN-009` — publish/unpublish/cancel controls.
10. `FE-031` — generic public Event Detail.
11. `FE-014B` — live Landing slider integration.
12. `EVS-007` — integration/security/regression gates.
13. `ACCEPT-EVENT-001` — isolated local Admin/public acceptance, rollback-gated controlled
    Production code deployment with the Event flag OFF, and safe Production smoke.

The owner replaced cloud Staging for this Event release because the single Upstash Free database is
Production-only. Do not use Production dependencies for local acceptance, perform Production write
tests, or enable dynamic navigation/feature flags during step 13. A separate owner launch approval
is still required. Each Task ID's preserved dependencies, acceptance criteria and security
requirements are in `tasks/<TASK_ID>.md`.

**Current Event checkpoint — 2026-10-10:** isolated local A–E, Quality Gate E, executable rollback,
controlled `e2ef4c0` Vercel/Render deployment and flag-OFF Production smoke are PASS.
`ACCEPT-EVENT-001` is complete. Stop before canonical Production data writes or enabling the flag;
both require a separate explicit owner launch decision.

## Stage 4 — Remaining P1/research backlog

Choose explicitly; do not infer priority from numeric Task ID:

- Settings/password: `AUTH-025 -> FE-024`.
- Event registration: `EVT-007`, then `ADMIN-011` and `FE-032`.
- Recap gallery: `ADMIN-EVT-002` after recap/media prerequisites.
- User Event list/calendar: `FE-030 -> FE-EVENT-CALENDAR-001` after stable APIs.
- Feedback: recontract before `FE-036`.
- Algorithm research: `MATCH-005/006`; never replace the Production V2 recommendation contract.
- RAG/campus/notifications/analytics/portfolio: allocate unique IDs and full contracts first.

## Stop conditions

Stop and report before continuing if any of these occur:

- health/readiness, authentication, authorization, cookie/CSRF/CORS/TLS or migration mismatch;
- unexpected data mutation, private-data exposure or stale cache across identities;
- email/Cron duplication, secret exposure or unbounded retry;
- WSS participant/origin failure or persisted-chat inconsistency;
- a required credential/account/operator approval is unavailable;
- a task is superseded, lacks a complete contract or depends on an incomplete predecessor.
