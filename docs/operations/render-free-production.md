# Render Free initial-production runbook

## Decision and release status

Render Free is the selected BuddyWebv2 API provider for the initial production rollout. Cloud Run
is dropped, Google Cloud billing is not required, and no paid Render upgrade is authorized. The
known Free-tier limits are an accepted operational risk, not a provider-selection blocker.

This decision does **not** make the release production-ready. Production remains blocked until the
remaining `ACCEPT-001` scenarios, staging maintenance evidence, minimum DR evidence and isolated
production resources all pass. DNS cutover is a later manual gate.

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

The existing staging frontend, Render service, Supabase project, Upstash database, buckets, Cron
jobs and secrets remain unchanged. Do not rename, repurpose, clone or promote them into production.
Create a separate Render web service connected to the reviewed `main` revision, and configure its
values individually; do not attach a staging environment group or copy a staging secret set.

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

Deploy first to the service's temporary `onrender.com` hostname with production resources but only
designated test accounts. Do not change DNS. Record UTC time, Git revision, database revision,
provider resource names, result and latency without recording credentials, cookies, user data or
provider response bodies.

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

The temporary Render hostname is suitable for health and direct HTTP/WSS diagnostics. Browser
cookie acceptance remains gated on the same-site `api.vgubuddyprogram.com` topology; do not weaken
the host-only Secure/SameSite cookie contract to make the temporary hostname appear production-ready.

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

1. Close `ACCEPT-001` using only its remaining staging scenarios.
2. Obtain deployed staging evidence for all three maintenance operations.
3. Complete an encrypted off-site backup and disposable DR restore rehearsal.
4. Confirm the no-cost Render, Supabase and Upstash capacity gates.
5. Provision isolated production resources and credentials.
6. Bootstrap the production database from zero to the verified Alembic head; create private buckets,
   Cron/Vault and Edge configuration.
7. Deploy the separate Render Free API on its provider hostname and complete safe acceptance.
8. Deploy a Vercel production preview and complete test-account acceptance.
9. Prepare, but do not execute, the `api`/`www` DNS cutover and rollback record.
10. After explicit cutover approval, change DNS, run smoke tests and retain the previous provider
    revisions/configuration needed for rollback.

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
