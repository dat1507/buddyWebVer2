# Controlling technical decisions

This is the compact decision layer. Full rationale and historical alternatives remain preserved in
the per-task extracts and legacy archive.

## Product and matching

- Buddy Matching V2 is recommendation-driven, not an Admin-run 1:1 assignment batch.
- Invitations are explicit; recipient Accept atomically creates an opposite-type ACTIVE Match and a
  single conversation. Users may have multiple Buddies; only duplicate active unordered pairs are
  forbidden.
- `student_type` becomes backend-locked once either participant has an ACTIVE Match. The frontend
  explains the lock but never owns the invariant.
- Recommendation eligibility is backend-authoritative: verified, complete, opted-in, current
  semester, opposite type and policy-compliant. Safe DTOs must not expose contact/private data.
- Invitation text is plain text, outer-trimmed, at most 500 non-whitespace runs and at most 10,000
  Unicode code points. Email and UI rendering must remain inert.
- Admin matching is monitoring-only. No run, preview, publish or manual override control belongs to
  the V2 release.

## Authentication and privacy

- FastAPI owns auth. Access/refresh credentials use Secure HttpOnly host-only cookies; CSRF uses the
  approved signed token contract; frontend session state is non-persisted and sanitized.
- USER registration never grants ADMIN. ADMIN creation uses the trusted CLI path.
- Role and verified-capability checks are backend dependencies, not UI-only guards.
- Logout/account switching clears private query/cache state; private responses use `no-store`.
- Production uses exact first-party origins, credentials and WSS origin validation. Do not relax
  SameSite/Secure/host-only behavior to accommodate temporary hostnames.

## Data, storage and semester safety

- PostgreSQL private application data remains outside automatic public Data API exposure. Runtime,
  migration, semester-backup and DR roles are distinct.
- Profile/Event media and semester backups use private Supabase Storage with backend-authorized
  lifecycle operations and bounded signed access.
- Semester Reset is guarded by re-authentication, phrase confirmation, write barrier, verified
  database+avatar backup and audit. Production deployment smoke is non-destructive.
- Any post-reset USER permanently blocks restoring the old cohort, even if the USER is later deleted.
- Alembic downgrade or manual `alembic_version` edits are not recovery procedures.

## Email, realtime and operations

- Transactional mail is a database outbox. Hosted delivery is Supabase Cron -> Edge Function ->
  Resend; the Python worker is fallback only and must not run concurrently.
- Chat persistence is authoritative; WebSocket/Redis provides realtime delivery and reconnects via
  REST history. Redis loss must not corrupt stored chat state.
- Health uses `/api/health/live` for process liveness and `/api/health/ready` for database, Redis,
  email and Storage readiness without exposing configuration.
- Secrets are generated per environment and never stored in Git, chat, `VITE_*`, command arguments
  or evidence.

## Deployment and release

- Frontend: Vercel project `buddy-web-ver2` rooted at `apps/web`.
- API: separate Render Free Docker web service, non-root Uvicorn on port 8000.
- Production uses isolated Supabase and production-only Redis prefixes/credentials. The approved
  Upstash reallocation means staging cannot use that Redis database.
- First-party topology is `www.vgubuddyprogram.com` -> Vercel and
  `api.vgubuddyprogram.com` -> Render.
- The reporting MVP may deploy while residual `ACCEPT-001` and complete DR evidence remain explicit
  post-deployment hardening. Data-integrity, auth/security, migration, startup/readiness, secret,
  cookie/CORS/TLS or core-flow failures still block closure.
- Dynamic Event/Admin Event surfaces remain feature-gated until the Part 27 chain and
  `ACCEPT-EVENT-001` pass. Static carousel content grants no dynamic-task credit.

## Phase 2 development order — owner decision 2026-10-08

- The first two Phase 2 development tasks are `FE-LANDING-BG-001`, then
  `FE-PROFILE-HOME-UNI-001`.
- Later order is Event system, Event Calendar, VGU Map, AI Assistant, Merchandise, then remaining
  enhancements; task-specific dependencies remain controlling.
- These isolated frontend tasks may be developed and committed on local `main` before Phase 1
  closure. Backup/DR, `PROD-001`, `SEM-008` and residual `ACCEPT-001` remain open and unchanged.
- Push to `origin/main` and Production deployment require a separate explicit owner approval.
- Home University is optional profile information only and must not affect Buddy Matching or
  recommendation weights.
