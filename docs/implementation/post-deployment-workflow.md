# Post-deployment workflow

This workflow is evidence-only unless the user separately authorizes Production interaction. It does
not authorize account creation, login, email sends, DNS/provider changes or destructive operations.

## Stage 1 — Close `PROD-001`

### 1. Preserve the deployed baseline

- Record current Git SHA, Vercel deployment and Render deployment/rollback point.
- Confirm `/live` and `/ready`; do not rerun migrations when Alembic is already at head.
- Confirm monitoring owners and a rollback decision channel before authenticated smoke.

### 2. Authenticated Admin smoke

- Use the designated Admin credential through the normal UI; never place it in commands/evidence.
- Verify login, direct refresh, Overview, Matching monitoring, User list/detail and non-destructive
  Semester status.
- Verify logout clears private UI/cache, `/api/auth/me` returns 401/no-store and protected re-entry is
  denied.
- Stop on role leakage, raw exception text, stale private data or unexpected mutation controls.

### 3. Complete the real two-USER core smoke

- Register and verify one second designated USER through the normal email path.
- Complete opposite-type profiles and matching preferences without operator-editing verification or
  synthesizing relationships.
- Verify Recommendations, invitation validation/send/email, recipient Accept, Current Buddies and
  one conversation with send/receive/read/reload.
- Verify foreign-user/resource denial and plain-text rendering; avoid maximum-volume or load probes
  unless separately approved.

### 4. First-party security/recovery smoke

- Inspect Secure HttpOnly host-only cookies, CSRF success/failure and session refresh/recovery.
- Prove exact-origin CORS and rejected foreign origin.
- Prove authenticated WSS Origin handling, reconnect and REST history recovery.
- Verify private cache removal after logout/account change.

### 5. Hold and rollback gate

- Observe health, error rate, email/Cron/outbox, Redis and WSS signals for the agreed period.
- Confirm rollback owners and that retained frontend/API deployments remain compatible with database
  head `0021`.
- Close `PROD-001` only with dated redacted evidence. Do not run Production Semester Reset/Restore.

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
13. `ACCEPT-EVENT-001` — real Admin/public staging acceptance.

Do not enable dynamic navigation/feature flags until step 13 passes. Each Task ID's preserved
dependencies, acceptance criteria and security requirements are in `tasks/<TASK_ID>.md`.

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
