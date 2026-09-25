# OPS-002 staging validation runbook

This is an early infrastructure gate, not a product release. Use only isolated staging resources;
never point these steps at production data, domains, credentials, email recipients or storage.

## Required topology

- Frontend: the existing Vercel project at `https://staging.vgubuddyprogram.com`, with Root
  Directory `apps/web`, HTTPS, SPA rewrites and the staging API origin.
- API: the existing WebSocket-capable FastAPI staging service. Frontend and API remain subdomains
  of the same registrable site.
- Email: PostgreSQL `transactional_outbox` -> Supabase Cron every minute -> Supabase `email-worker`
  Edge Function -> Resend.
- Database: isolated Supabase staging with distinct least-privilege runtime and migration roles.
- Redis: isolated TLS staging database with environment-specific namespaces.
- Storage: private Supabase buckets; browser clients receive only short-lived signed access.

Google Cloud VM and paid Render Background Worker are not deployment dependencies. The existing
Python worker remains local/debug/fallback tooling until the Edge implementation passes acceptance;
do not run it as a second production scheduler.

## Email-worker deployment gate

Follow [the Supabase email-worker runbook](supabase-email-worker.md) in order. Stop before secrets
are needed and have an owner enter them directly in the Supabase Dashboard; no secret value belongs
in chat, source, CI output or acceptance evidence.

The hosted path must use the existing `vgu_buddy_runtime` database role through the Supabase
transaction pooler with TLS. It must not use the migration owner, `postgres`, DB password exposed to
clients, a Supabase secret/service-role key, or a public-schema `SECURITY DEFINER` RPC.

Acceptance requires:

- migration `0010_edge_email_outbox_functions` applied;
- Cron and `pg_net` enabled in the staging project;
- `email-worker` deployed with its six server-only secrets;
- two Cron-only values stored in Vault;
- the case-sensitive `vgu-buddy-email-worker-every-minute` job scheduled as `* * * * *`;
- empty queue, normal verification delivery, idempotency, retry/recovery, two-call overlap and
  20-row batch-bound tests passed against staging;
- redacted Cron/Function/outbox evidence with no credentials, recipient, body or verification URL;
- Supabase and Resend usage confirmed inside Free-plan quotas with no paid add-on.

The database claim is atomic: a single statement selects ready rows with `FOR UPDATE SKIP LOCKED`
and updates their five-minute leases. Each invocation has a unique owner, finalization requires that
owner, and the lease is longer than the Free-plan 150-second Edge wall-clock limit. Overlapping
minute schedules therefore cannot claim the same row. Resend receives the stable database
idempotency key to cover a lost acknowledgement before finalization.

## Backend security configuration

Set these values in server-only stores, never in Vercel build variables:

- `APP_ENV=production`
- exact `CORS_ALLOWED_ORIGINS=https://<staging-frontend>`
- `AUTH_COOKIE_SECURE=true`
- exact `PUBLIC_APP_BASE_URL=https://<staging-frontend>`
- independent JWT, CSRF and email-sealing keys
- staging-only database, `rediss://`, Storage and email credentials

Never set Uvicorn `--forwarded-allow-ips=*`. Keep the ingress trust boundary fail-closed until the
provider publishes a narrower, tested peer range.

## Migration and rollback gate

1. Capture a timestamped off-site logical backup with byte size and SHA-256 before migration.
   Supabase Free does not imply a managed daily-backup entitlement.
2. Restore every portable application-owned object into a separate disposable compatible target,
   preserving provider-managed schemas. Verify the baseline, migrate to head, downgrade and
   restore/re-apply migrations. Never restore over active staging for rehearsal.
3. Run `python -m alembic -c pyproject.toml upgrade head` with only the migration credential.
4. Start API and Edge delivery with only least-privilege runtime credentials; verify runtime roles
   cannot perform migration-owner DDL.
5. Record the application rollback artifact and database recovery decision. Roll code back only
   while its schema remains compatible.

## Application smoke gate

Record UTC timestamp, commit, deployment URLs, resource identifiers and pass/fail without copying
tokens, cookies, signed URLs, email addresses or provider response bodies.

- API liveness and readiness pass with database/Redis `ok` and email/Storage `configured`.
- WSS accepts the exact frontend Origin and rejects an unrelated Origin.
- SPA deep links load directly.
- Registration, login, refresh/reload, logout and profile update work across real HTTPS origins.
- Avatar access remains private and anonymous object access is denied.
- A verification request reaches only the designated staging mailbox; confirmation succeeds once
  and replay fails generically.
- Redis outage behavior fails closed and recovers without exposing connection details.

## Capacity and completion

The once-per-minute job is approximately 43,200 invocations per 30-day month against the current
500,000 Free Edge invocation allowance. Monitor database size, Storage, egress, function limits and
Resend's current 3,000/month and 100/day Free quota; report pressure rather than enabling a paid
plan. Capacity is based on measured verification/invitation volume, not the approximate 150-user
account count alone. A 150-user same-day verification burst exceeds the Free daily allowance.

OPS-002 is complete only when backup/rollback, migration, application smoke and deployed email
acceptance all pass and sanitized evidence is recorded. Local/fake tests do not replace the deployed
gate. Matching invitation and invitation-accepted email acceptance remains pending until those
application flows are implemented.
