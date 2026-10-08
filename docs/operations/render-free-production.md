# Render Free initial-production runbook

## Decision and release status

Render Free is the selected BuddyWebv2 API provider for the initial production rollout. Cloud Run
is dropped, Google Cloud billing is not required, and no paid Render upgrade is authorized. The
known Free-tier limits are an accepted operational risk, not a provider-selection blocker.

This decision does **not** by itself close the production release. The 2026-10-07
[production MVP readiness record](production-mvp-readiness-2026-10-07.md) supersedes the earlier
all-or-nothing release classification: full `ACCEPT-001` sign-off and the complete DR rehearsal stay
OPEN as post-deploy hardening, while isolated resources, secrets, safe migration, provider-host
acceptance, first-party DNS, health and core-flow smoke tests remain blocking gates. First-party DNS,
owner functional acceptance and authenticated cookie/WSS recovery later passed on 2026-10-08. The
private Semester backup, retained backend rollback point, named owners and post-repair hold remain
open as recorded in `../implementation/production-status.md`.

## Audited production topology

```text
https://www.vgubuddyprogram.com
    -> Vercel production frontend
    -> https://api.vgubuddyprogram.com
    -> separate Render Free production web service
       -> separate Supabase production project
       -> separate TLS Upstash Redis database
       -> private production Supabase Storage buckets

transactional_outbox
    -> production Supabase Cron
    -> production email-worker Edge Function
    -> production Resend sender

production Supabase Cron
    -> POST https://api.vgubuddyprogram.com/api/internal/maintenance
```

The existing staging frontend, Supabase project, buckets, Cron jobs and secrets remain unchanged.
Create a separate Render web service connected to the reviewed `main` revision, and configure its
values individually; do not attach a staging environment group or copy a staging secret set.

**Owner-approved Redis exception — 2026-10-07:** the sole Free Upstash database may be reallocated
from staging to production only after every staging consumer is detached, the keyspace is audited,
old credentials are rotated and production-only prefixes are configured. It must never be shared
between staging and production. The Render staging API was suspended and its public endpoint showed
the provider's owner-suspended response. Upstash Data Browser was empty and an independent CLI
`DBSIZE` returned `0`, so no `FLUSHDB`, `FLUSHALL`, `DEL`, or `UNLINK` was required or run. The owner
then completed the credential reset; Upstash reported `Password successfully reset`, and a second
`DBSIZE` returned `0`. The database was renamed to `vgu-buddy-production`. Render staging remains
`Suspended by you`; its former Redis credentials are invalid and may not be replaced with the new
production credentials. Staging Redis may be provisioned later on another account.

The repository contains no `render.yaml`, so service creation, compute-plan selection, health path,
custom domain and environment configuration are explicit Render Dashboard gates. The API container
is compatible with Render's Docker service: it runs as a non-root user, listens on
`0.0.0.0:8000`, exposes HTTP/WebSocket on one public port, and writes sanitized structured logs to
stdout/stderr. Use `/api/health/live` as the Render health path; keep
`/api/health/ready` as the dependency-aware release gate.

## Free-capacity gates before provisioning

Current provider documentation permits more than one Free web service in a Hobby workspace, but
all Free web services in that workspace share **750 running instance-hours per calendar month**.
A continuously active production service consumes about 720 hours in a 30-day month or 744 hours
in a 31-day month, leaving only about 30 or 6 hours respectively for an active staging service.
Spun-down time does not consume hours. BuddyWebv2's authenticated unread WebSocket can keep an
instance active while messages continue, so the Render Billing usage page must be checked before
creating the production service and monitored after launch. Exhaustion suspends all Free web
services in the workspace until the next month.

Render Hobby currently allows up to 25 services, so the documented platform limit does not itself
force staging/production reuse. The owner must still confirm the account's current service count,
included usage and absence of an automatic paid action. Do not create another workspace or add a
payment method merely to bypass this gate without a separate decision.

Supabase currently grants two active Free projects across organizations where the account is an
Owner or Administrator. Production can be the second project only if the dashboard confirms a Free
slot. A paused project does not count, but no project may be paused or deleted as part of this
runbook. Upstash's current public pricing material is not sufficiently unambiguous about a second
Free database for the existing account; the dashboard must explicitly offer a distinct production
database at `$0` before creation. If it does not, stop and report the constraint instead of sharing
the staging database, adding billing or changing the isolation contract.

The authenticated dashboard gate was run on 2026-10-07. The account has one existing Free Tier
database, previously named `vgu-buddy-staging`; opening **Create Database** reports **“You can create
1 database in free tier”** and requires a payment method for additional databases. The owner chose
the reviewed reallocation path above instead of billing or concurrent resource sharing.

The Supabase production capacity/bootstrap gate passed later on 2026-10-07. Project
`vgu-buddy-production` (`tvzyohsuaueacabisylq`) is a healthy Free/Nano project in Singapore. Its
empty database was migrated through the provider's TLS session pooler and Alembic reported
`0021_restore_runtime_permissions (head)`. The migration-owner password was kept ephemeral and is
not a Render secret. After explicit owner confirmation, the migration-created
`vgu_buddy_runtime` login received a new production-only password. A sanitized connection check
proved that this role can log in through the same TLS session pooler, and the SQL editor independently
confirmed the single `public.alembic_version` row at head. The runtime credential was not persisted
or exposed and is reserved for the new production Render service.

## Production configuration contract

Generate new production values. A same variable name across environments does not authorize reuse
of its value.

| Location | Setting | Production contract |
| --- | --- | --- |
| Render only | `DATABASE_URL` | production `vgu_buddy_runtime` role, TLS, production Supabase only |
| Render only | `DATABASE_BACKUP_URL` | production semester-backup role with its existing table allowlist; not the DR or migration role |
| Operator machine only | `DATABASE_MIGRATION_URL` | production migration owner for zero-to-head Alembic bootstrap; never add to Render |
| Operator/DR store only | DR database credential | distinct reviewed `vgu_buddy_dr_backup`; never add to Render or reuse the semester role |
| Render only | `APP_ENV` | `production` |
| Render only | `REDIS_URL`, `RATE_LIMIT_STORAGE_URI` | same separate production Upstash TLS `rediss://` endpoint |
| Render only | `REDIS_KEY_PREFIX` | production-only operations namespace satisfying the `:production:` validator |
| Render only | `RATE_LIMIT_KEY_PREFIX` | production-only authentication namespace satisfying the `:production:` validator |
| Render only | `AUTH_JWT_SECRET`, `AUTH_CSRF_SECRET` | two newly generated independent keys |
| Render only | `AUTH_COOKIE_SECURE` | `true` |
| Render only | `CORS_ALLOWED_ORIGINS` | exact `https://www.vgubuddyprogram.com`, with no wildcard |
| Render + Edge | `PUBLIC_APP_BASE_URL` | exact `https://www.vgubuddyprogram.com` |
| Render + Edge | `EMAIL_VERIFICATION_SEALING_KEY` | one new production key shared only by these two runtimes |
| Render only | `SUPABASE_URL`, `SUPABASE_SECRET_KEY` | production project and server-only key; never expose through `VITE_*` |
| Render only | `MAINTENANCE_WORKER_CRON_SECRET` | new production Cron/API secret, also stored in production Vault |
| Edge only | outbox DB URL, Resend key/sender, email Cron secret | production-only values following the email-worker runbook |
| Vercel build | `VITE_API_URL` | `https://api.vgubuddyprogram.com/api` only after the temporary-host acceptance passes |

Production database bootstrap starts from an empty Supabase project and runs
`python -m alembic -c pyproject.toml upgrade head` from a trusted local operator machine. Confirm
the exact source head and `public.alembic_version` afterward. Never clone staging data and never
put the migration credential in the Render runtime.

Create the existing private Storage buckets through the committed server-only commands against the
production project. Configure the production email outbox path as Supabase Cron -> Edge Function ->
Resend and do not run the Python fallback worker concurrently. No writable application state may
depend on Render's ephemeral filesystem.

## Render Free acceptance record

The API was deployed and first-party DNS was cut over by 2026-10-08. The checklist below is retained
as the acceptance contract; reuse completed evidence and run only the missing authenticated checks.
Record UTC time, Git revision, database revision, provider resource names, result and latency without
recording credentials, cookies, user data or provider response bodies.

1. Prove a warm and an intentionally idle/cold request to `/api/health/live`; record latency and
   confirm the cold start delays rather than fails.
2. Prove `/api/health/ready` reports the production database, Redis, Storage and email dependencies
   ready without disclosing connection details.
3. Prove registration/login, session restoration, Secure host-only cookies, CSRF acceptance and
   cross-origin rejection through the eventual first-party topology.
4. Prove recommendations, invitation send/accept and the designated transactional emails.
5. Prove conversation and unread WebSockets connect, exchange messages, reconnect after idle or a
   deploy/restart, reconcile through REST, and use production Redis Pub/Sub.
6. Record warm API latency, post-idle latency and logs for one controlled redeploy/restart. Confirm
   local filesystem loss is irrelevant.
7. Confirm the separate production Cron/Edge email worker and maintenance Cron are the only hosted
   schedulers, and that their sanitized provider evidence is present.
8. Confirm rollback can select one of Render Free's retained recent deploys without a database
   downgrade. Do not use keepalive traffic to defeat spin-down.

**Direct dashboard update — 2026-10-08:** the Production Render service reported only one deploy,
`dep-db343nu7bikc73bjvalg` at application commit `d15cb1d7`. The service is Live and public health is
healthy, but no previous Render deploy is currently selectable. This checklist item is BLOCKED until
an owner establishes a compatible retained deploy or approves an immutable redeploy procedure. No
redeploy or rollback was performed during verification.

The temporary Render hostname remains suitable for health and direct HTTP/WSS diagnostics. Browser
cookie acceptance was proved on 2026-10-08 on the live same-site `api.vgubuddyprogram.com`
topology; preserve that evidence and do not weaken the host-only Secure/SameSite cookie contract.

## Accepted limitations and paid reevaluation

Accepted at launch:

- spin-down after 15 idle minutes and roughly one-minute wake-up delay;
- one instance only, lower CPU/RAM, no autoscaling and provider-initiated restarts;
- ephemeral filesystem, no shell/SSH and no one-off jobs;
- shared workspace instance-hours, bandwidth and build-minute limits;
- WebSocket interruption on deploy/restart and the need for client reconnect/reconciliation;
- community-level support and no production SLA.

Classify incidents before recommending an upgrade: normal first request after idle is cold start;
application exceptions are bugs; readiness failures identify database/Redis/provider dependencies;
WebSocket close around deploy/restart is lifecycle behavior; sustained CPU saturation, queueing or
memory termination is compute pressure.

Reevaluate paid Render only from repeated production evidence across more than one observation
window, such as user-visible warm latency, repeated timeouts/5xx, cold wake-ups that fail instead of
delay, abnormal reconnect loops, Free-limit suspension, sustained resource exhaustion, or recurring
incidents attributable to compute. One incident is not an automatic upgrade trigger. Document the
measurements and obtain separate approval before changing the compute plan.

## Deployment order and rollback boundary

1. Preserve the accepted deployed staging evidence for all three maintenance operations. **PASS on
   2026-10-04 for commit `5b20c00`.**
2. Confirm the no-cost Render, Supabase and Upstash capacity gates. **PASS.**
3. Provision isolated production resources and credentials. **PASS for the deployed MVP.**
4. Bootstrap the production database from zero to the verified Alembic head; create private buckets,
   Cron/Vault and Edge configuration. **PASS at `0021`; public readiness is healthy.**
5. Deploy the separate Render Free API on its provider hostname and complete core safe acceptance.
   **Deployment/public health PASS; authenticated core acceptance remains open.**
6. Deploy Vercel and complete test-account acceptance. **Deployment/API target PASS; the complete
   two-USER and Admin smoke remains open.**
7. Prepare and execute the approved `api`/`www` DNS cutover with rollback record. **DNS PASS by
   2026-10-08; rollback/hold evidence remains open.**
8. Run post-cutover smoke and retain the previous provider revisions/configuration needed for
   rollback. **Public health/auth-boundary/CORS PASS; authenticated cookie/WSS/core-flow smoke is
   open.**
9. Complete the deferred signed acceptance matrix, encrypted off-site backup and disposable DR
   rehearsal promptly after the progress-reporting release; do not mark them done before evidence.

Never run destructive Semester Reset/Restore acceptance against production user data. A code
rollback must remain schema-compatible; database recovery follows the DR runbook, not an improvised
Alembic downgrade or direct edit of `alembic_version`.

## Current references

- [Render Free limitations](https://render.com/docs/free)
- [Render WebSockets](https://render.com/docs/websocket)
- [Render workspace limits](https://render.com/docs/platform-features-by-plan)
- [Supabase Free project limits](https://supabase.com/docs/guides/platform/billing-on-supabase)
- [Upstash Redis pricing](https://upstash.com/pricing/redis)
- [Supabase maintenance worker](supabase-maintenance-worker.md)
- [Supabase email worker](supabase-email-worker.md)
- [Supabase Free off-site DR](supabase-free-offsite-dr.md)
