# Supabase transactional email worker

Production delivery uses this bounded, scheduled path:

```text
transactional_outbox
    -> Supabase Cron (once per minute)
    -> email-worker Edge Function
    -> Resend
```

The Python command `python -m app.cli email-worker` remains supported for local development,
debugging and fallback. It is not the hosted deployment dependency after this Edge path passes
staging acceptance.

## Preserved MAIL-001 contract

- Business transactions still insert into `app_private.transactional_outbox`; no application
  enqueue path or table contract is replaced.
- `idempotency_key` remains unique in PostgreSQL and is sent unchanged as Resend's
  `Idempotency-Key` header.
- The Edge worker claims at most 20 rows per invocation. Its database entry point rejects values
  outside `1..100`, and delivery concurrency is capped at five.
- Claim is one SQL statement using `FOR UPDATE SKIP LOCKED` followed by the lease update in the same
  statement. A five-minute lease is longer than the Free-plan 150-second Edge wall-clock limit.
- Success/failure finalization requires the same `lease_owner`. Retry delays remain 1, 2, 4 and 8
  minutes; the fifth failed attempt is terminal. Expired leases are recoverable.
- The existing AES-GCM verification payload and plain-text template contract are reused. Matching
  invitation and invitation-accepted event/templates do not exist yet and remain separate feature
  work.

Two Cron calls may overlap. They receive different worker IDs. PostgreSQL row locks plus
`SKIP LOCKED` let only one claim a ready row, and the committed five-minute lease excludes later
claims during the invocation. If Resend accepts a request but the worker loses the acknowledgement,
the recovered attempt uses the same provider idempotency key; Resend retains keys for 24 hours.
This proves duplicate prevention for overlapping Edge invocations and normal lease recovery. As
with the Python worker, an outage lasting beyond the provider's idempotency-retention window cannot
offer strict distributed exactly-once delivery and must remain an operational alert.

## Required secrets and least privilege

Configure these only in **Supabase Dashboard -> Edge Functions -> Secrets**:

- `OUTBOX_DATABASE_URL`: transaction-pooler URI for the existing `vgu_buddy_runtime` role, with TLS;
  do not use the migration owner, `postgres`, or a Supabase secret/service-role key.
- `RESEND_API_KEY`
- `EMAIL_FROM_ADDRESS`
- `PUBLIC_APP_BASE_URL`
- `EMAIL_VERIFICATION_SEALING_KEY`: the same key used by the API that seals verification payloads.
- `EMAIL_WORKER_CRON_SECRET`: a new high-entropy random value used only for Cron-to-Function auth.

Do not paste values into issue text, chat, logs, command arguments or tracked files. A populated
`.env` remains ignored. The function returns only counts/error codes and never logs recipients,
message bodies, database URLs or credentials.

Store two values in **Supabase Dashboard -> Project Settings -> Vault**:

- `buddy_project_url`: the project's `https://<project-ref>.supabase.co` origin.
- `buddy_email_worker_cron_secret`: exactly the same value as `EMAIL_WORKER_CRON_SECRET`.

Vault is used only by the database Cron command. Edge Function Secrets hold the six runtime values.

## Deployment order

1. Apply Alembic migration `0010_edge_email_outbox_functions` with the migration credential.
2. In the Supabase Dashboard, open **Integrations -> Cron** and enable Cron; enable the `pg_net`
   extension if the Cron form reports it unavailable.
3. Add the six Edge Function secrets and the two named Vault entries above without exposing their
   values.
4. Deploy `supabase/functions/email-worker` with JWT verification disabled as committed in
   `supabase/config.toml`.
5. In **SQL Editor**, run `supabase/cron/email-worker.sql`. Its case-sensitive job name is
   `vgu-buddy-email-worker-every-minute`; running it again updates that job rather than duplicating
   it.
6. Run the staging acceptance below before declaring the Python worker retired. Do not run both as
   production schedulers during acceptance; the Python path is fallback only.

## Acceptance and recovery

Record sanitized evidence for:

1. Empty queue: a manual invocation returns zero counts.
2. Normal delivery: request verification for a designated staging account and confirm one Resend
   delivery plus one successful, single-use verification.
3. Idempotency: retry the same claimed job and confirm one provider delivery for its key.
4. Retry: simulate one retryable provider failure and confirm the row moves to the next attempt,
   then succeeds without a duplicate.
5. Concurrency: issue two authenticated function calls together and confirm their total claim/send
   count for one row is one.
6. Bounded batch: enqueue more than 20 ready rows and confirm one invocation claims exactly 20.

Inspect `cron.job_run_details`, Edge Function invocation/log views and sanitized outbox state. A
failed invocation needs no always-on process: an unfinalized row becomes eligible after the
five-minute lease, and provider-side idempotency covers the acknowledgement gap. Disable the Cron
job before any manual fallback worker is started.

The function emits one fixed-field JSON `email_worker_invocation_completed` event containing only
status, duration, controlled outcome and aggregate counts. Use the read-only
[`email-worker-health.sql`](../../supabase/monitoring/email-worker-health.sql) snapshot and the
[OPS-003 observability runbook](ops-003-observability.md). For provider outage, terminal-row
reconciliation or fallback activation, follow the [OPS-003 recovery runbook](ops-003-recovery.md);
do not inspect or log recipient, payload, verification link, idempotency key or provider ID.

## Free-plan capacity

At one invocation per minute, Cron produces about 43,200 Edge invocations in a 30-day month. The
current Free allowance is 500,000 Edge invocations/month. The hosted Edge limits relevant here are
150 seconds wall clock, 2 seconds CPU per request and 256 MB memory. This bounded I/O worker is
designed to stay below those limits; quota monitoring remains required. Supabase documents Cron as
available through its hosted `pg_cron` module and supports scheduled Edge calls through `pg_net`.
Resend Free currently allows 3,000 emails/month and 100/day. Approximately 150 registered users is
compatible only when transactional mail is distributed below that daily limit; onboarding all 150
users on one day is not a Free-plan-supported workload. There is no mandatory monthly worker charge
while the Supabase project and Resend account remain on their Free plans and within those quotas. No
automatic paid upgrade is authorized.
