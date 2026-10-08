# Production MVP readiness — 2026-10-07

## Release decision

The repository revision under review is `d15cb1d7c380e12e8f66e38f5573d191415d6913`.
It is a **deployable MVP candidate** for progress reporting. No known application-code defect now
meets the production-blocker definition for data integrity, authentication/authorization, the core
Buddy flow, process startup, or migration safety.

This decision intentionally does not close the full `ACCEPT-001` contract or the complete DR plan.
Those records stay OPEN where evidence is still missing. The release boundary is the smaller MVP
described here, and the remaining hardening work is explicitly deferred rather than marked done.

The mandatory production gates are now infrastructure and configuration gates: isolated resources,
new production secrets, zero-to-head migration, provider-host acceptance, first-party DNS, and core
smoke tests. A failure at any of those gates stops the rollout.

## Closed manual gate

`restore-blocked-after-new-USER` is **PASS / CLOSED**. The guarded execution completed with
`RESTORE_BLOCKED_NEW_DATA`; the new USER and current-semester marker remained present; the backup
was not marked restored; affected/result counts remained empty; and the aggregate USER, profile,
invitation, Match, conversation, and message baseline was unchanged. The detailed redacted evidence
is in [the ACCEPT-001 reconciliation record](accept-001-reconciliation-2026-10-04.md).

## Production email-verification incident — 2026-10-08

**Incident closed; full Buddy lifecycle smoke is capacity-gated.** The registration and resend
requests succeeded and created verification tokens plus transactional-outbox rows, but the
production email runtime had not been provisioned. Render correctly contained only the web API;
Supabase had no deployed `email-worker`, Edge secrets, `pg_cron`/`pg_net`, Vault entries, or email
Cron job. Consequently, both affected outbox rows remained `pending` with `attempts = 0`, and the
production Resend key showed no request or use for them. This was an operational omission in rollout
gate 5, not a mailbox/spam conclusion or a Resend/DNS failure.

The minimal production fix deployed the repository's `email-worker`, added its six required Edge
secrets, enabled `pg_cron` and `pg_net`, added the two named Vault entries, disabled legacy JWT for
the function's committed custom `x-cron-secret` authentication, and scheduled exactly one active
`vgu-buddy-email-worker-every-minute` job. The first authenticated invocation returned HTTP 200,
claimed the two expired rows, and terminally failed both with controlled error code
`verification_link_expired`; no stale email was sent. The following scheduled invocation returned
HTTP 200 with all aggregate counts zero, proving the production Cron-to-Function path is healthy
with an empty queue. No USER verification state was edited, no USER was deleted, no DNS record or
Resend key was changed, and no bulk retry was performed.

After operator confirmation, the application requested exactly one new verification email for the
same designated test USER. The new outbox row was initially `pending`, then the next scheduled worker
invocation moved it to `sent` with `attempts = 1`, no error, and no retry. Resend recorded the matching
message as `Delivered`. The user opened that message and completed the normal product link flow; the
Settings UI then reported `Verified`, and a read-only database check confirmed an active USER with a
non-null `email_verified_at`. No verification state was edited by an operator.

The post-verification Buddy smoke reached Recommendations, Invitations, and My Buddies without a
verification gate or browser error. Each returned its valid empty state. At that time, a sanitized
database count confirmed that the current semester contained zero other USER accounts, so the empty
set is expected and an invitation/accept/Match lifecycle cannot be exercised without provisioning a
second designated test USER. No extra USER or synthetic relationship was created for this smoke.

## Production Admin test account — 2026-10-08

Before provisioning, a read-only production query confirmed zero existing ADMIN accounts and no
duplicate for the designated test alias. Because the Render Free service provides neither Shell/SSH
nor one-off jobs, the repository's `create_admin` transaction was executed locally against the
production runtime connection without placing the connection string or account credentials in Git,
chat, command arguments, process listings, or evidence. A post-create read-only query confirmed
exactly one ADMIN satisfying the account contract: active, not deleted, legacy Admin verification
set, no USER-semester membership, and a cost-12 bcrypt password hash. The generated login credential
was handed to the operator through the local clipboard only. Admin login/UI smoke remains pending.

## Release-candidate verification

Run on 2026-10-07 against the reviewed checkout:

- web: Prettier, ESLint, TypeScript, 721 tests, and Vite production build PASS;
- API on the Docker/CI Python 3.12 line: dependency consistency, Ruff, strict mypy over 273 source
  files, 1,330 tests PASS with 37 explicitly environment-gated live tests skipped;
- API package sdist/wheel build PASS;
- Alembic reports exactly one head: `0021_restore_runtime_permissions`;
- `git diff --check` PASS.

A Starlette test-client WebSocket teardown can intermittently raise `CancelledError` under the local
Python 3.14 environment. The same test and the complete realtime set pass on Python 3.12, which is
the pinned Docker/CI runtime. This is a test-harness/runtime compatibility item, not evidence that
the deployed chat flow is broken.

## First-party cutover and public smoke — 2026-10-08

Read-only checks at 2026-10-08 10:27 Asia/Saigon confirmed that the cutover has occurred:

- `api.vgubuddyprogram.com` CNAMEs to `vgu-buddy-api-production.onrender.com`;
- `www.vgubuddyprogram.com` CNAMEs to `3d95265b44dec908.vercel-dns-017.com`;
- `/api/health/live` and `/api/health/ready` returned 200; readiness reported database and Redis
  `ok` plus email and Storage `configured`;
- the deployed frontend bundle targets `https://api.vgubuddyprogram.com/api`;
- deployed bundle `index-DIl7WhwA.js` contains all five static Event titles introduced by the latest
  committed carousel update `81979ce`;
- anonymous `/api/auth/me` returned 401 with `Cache-Control: no-store`;
- login CORS preflight allowed the exact `https://www.vgubuddyprogram.com` credentialed origin and
  rejected an unrelated origin.

These observations close the public DNS/readiness/CORS portion of the rollout. They do not prove
authenticated Admin/session/cookie, full Buddy lifecycle, WSS, Semester guard, hold-period or
rollback acceptance. The focused current record is
[`docs/implementation/production-status.md`](../implementation/production-status.md).

## Remaining release-closure gates after DNS cutover

These items are rollout gates, not reasons to add unrelated application features:

1. **Upstash reallocation gate — PASS / CLOSED on 2026-10-07.** The authenticated dashboard confirmed
   that the account's only Free slot is the database previously named `vgu-buddy-staging`. The owner
   explicitly authorized reallocating that database to production, with no simultaneous
   staging/production use. Read-only evidence showed Data Browser empty and `DBSIZE = 0`; no Redis
   value was inspected. The only Render staging API consumer was then suspended, and its public API
   endpoint returned the provider's owner-suspended response. No local API/worker process has a
   configured Upstash URL. No `FLUSHDB`, `FLUSHALL`, `DEL`, or `UNLINK` is necessary or authorized.
   The owner completed the credential reset; Upstash reported `Password successfully reset`, and a
   post-rotation `DBSIZE` again returned `0`. The database is now named `vgu-buddy-production`.
   Render `vgu-buddy-api-staging` remains `Suspended by you`, so the rotated TLS Redis endpoint is
   production-only. No Redis value or credential was recorded, and no delete/flush command ran.
2. **Supabase production bootstrap — PASS through migration on 2026-10-07.** The Free/Nano project
   `vgu-buddy-production` (`tvzyohsuaueacabisylq`) is healthy in Singapore. Automatic Data API table
   exposure is disabled and automatic RLS is enabled. The empty database was migrated over a TLS
   session-pooler connection; Alembic reports `0021_restore_runtime_permissions (head)`. The
   migration-owner password was neither persisted nor exposed. The separate Render Docker web
   service is now deployed and its public readiness database probe passes; staging resources remain
   unchanged apart from the approved Redis exception.
3. **Database runtime credential — PASS on 2026-10-07.** A new password was assigned to the
   migration-created `vgu_buddy_runtime` login only after owner confirmation. A sanitized diagnostic
   verified that the role exists, can log in, has a password, and connects through the production TLS
   session pooler. The production SQL editor independently confirmed one `public.alembic_version` row
   at `0021_restore_runtime_permissions`. The credential was not persisted or exposed and was
   reserved for the now-deployed production Render service. The public database/Redis readiness
   probes pass; no secret value belongs in this record, Git, chat, `VITE_*`, or a shared staging
   environment group.
4. **Migration gate — PASS.** The empty production database was bootstrapped zero-to-head and
   `public.alembic_version` was verified by Alembic as `0021_restore_runtime_permissions`. Never put
   the migration owner credential in Render and never improvise a downgrade.
5. **Public dependency path — PASS.** Production Storage/email report configured, the email
   Edge/Cron path delivered and consumed one fresh verification message, and `/api/health/ready`
   returned 200 without connection detail.
6. **Deployment/public startup — PASS; authenticated core smoke — PARTIAL.** The API and frontend are
   deployed and public live/readiness pass. Registration/email verification reached normal verified
   state, but authenticated session recovery, a complete two-USER invitation/Match/chat flow, Admin
   login and the non-destructive Semester UI guard still need dated evidence.
7. **DNS/API target/basic CORS — PASS; cookie/session evidence — OPEN.** The first-party CNAMEs,
   frontend `VITE_API_URL`, HTTPS and exact-origin preflight are live. Secure host-only cookie,
   refresh/session and authenticated WSS behavior still require first-party smoke.
8. **Post-cutover public smoke — PASS; full release hold — OPEN.** Any data-integrity,
   auth/security, core-flow, migration, startup, readiness, cookie, CORS, WSS or TLS failure remains
   release-blocking. Close `PROD-001` only after authenticated smoke, observation and rollback
   evidence.

## DEFER — post-deploy hardening

| Item | Severity | Why it is deferred for this milestone |
| --- | --- | --- |
| Deployed inert rendering evidence for maximum-length invitation text | Low | Validation is enforced; missing evidence is presentation/acceptance completeness, not a core-flow or integrity failure. |
| True stale-tab type-change UX and isolated Accept-versus-type-update race/load evidence | Medium | Existing transactional guards reject the invalid state and preserve the Match; the remaining gap is rare concurrency/UX evidence. |
| Physical deletion evidence for expired messages and broader retention housekeeping | Medium | Reads already exclude expired data and maintenance is bounded; physical cleanup is operational retention work. |
| Consolidated signed/redacted `ACCEPT-001` owner record | Low | Evidence administration remains OPEN but does not change runtime behavior. |
| Full candidate matrix for non-core live cases and complete accessibility sweep | Medium | Core production smoke remains mandatory; the exhaustive acceptance matrix can follow the reporting milestone. |
| Encrypted off-site snapshot plus disposable full DR restore rehearsal | High | Explicitly accepted as post-deploy for this MVP; safe migration and provider rollback remain mandatory. This stays OPEN and must be scheduled promptly. |
| Render cold-start/load observation, Free-hour monitoring, and paid-plan reevaluation | Medium | Known Free-tier operational risk; not a correctness blocker unless it causes actual health/core-flow failure. |
| Vite bundle-size advisory and test-harness Python 3.14 teardown flake | Low | Performance/tooling hardening; the production Python 3.12 suite and builds pass. |
| Legacy Gemini credential revocation before any future Gemini/chatbot work | Medium | No detected credential or Gemini integration exists in this repository or current release; the legacy key must never be reused. |
| API-backed Event/Admin content tracks feature-gated outside the MVP | Low | Unrelated to the required Buddy progress-reporting flow. |

## Production contract

- Backend: separate Render Free Docker web service; image starts non-root Uvicorn on port 8000.
- Frontend: Vercel project `buddy-web-ver2`, root `apps/web`; build with `npm ci` then
  `npm run build`; publish `dist`.
- Database/Storage: separate Supabase production project; private buckets; runtime, migration,
  semester-backup, and DR credentials remain distinct.
- Redis: the detached, empty Upstash TLS `rediss://` database reallocated by owner decision, with
  rotated credentials and production-only key prefixes. Staging remains suspended and may not use
  this database after reallocation.
- Email: Supabase Cron -> `email-worker` Edge Function -> Resend; the local Python worker is fallback
  only and must not run concurrently.
- Scheduler: a separate production maintenance Cron calls
  `POST https://api.vgubuddyprogram.com/api/internal/maintenance`; email and maintenance secrets are
  newly generated and independently scoped.
- Health: Render probes `/api/health/live`; `/api/health/ready` is the dependency-aware release gate.
- Domains: `www.vgubuddyprogram.com` -> current Vercel project;
  `api.vgubuddyprogram.com` -> production Render service.

Required Render variables are the contracts documented in
[the Render Free runbook](render-free-production.md): database/runtime URLs, production TLS Redis
URLs and prefixes, independent JWT/CSRF keys, secure-cookie and exact-origin settings, public base
URL, email sealing key, production Supabase server values, maintenance Cron secret, and Resend/sender
configuration. `DATABASE_MIGRATION_URL` remains operator-only. Vercel receives only the production
`VITE_API_URL` and non-secret feature flags.

## Rollback boundary

Keep the current staging services and old `www` Vercel project unchanged until cutover. Vercel can
promote/restore the previous production deployment; Render can select a retained recent deployment.
Application rollback must remain compatible with migration head `0021`; database recovery follows
the DR runbook, never an ad-hoc Alembic downgrade or direct `alembic_version` edit. DNS rollback
returns `www` to the preserved old Vercel project and removes/reverts the `api` record if the
first-party release gate fails.
