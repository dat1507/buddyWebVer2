# OPS-003 deployment, migration and outage recovery runbook

Every action starts with an incident UTC timestamp, environment, current application commit,
current Alembic revision, provider deployment identifiers and an operator. Record identifiers only;
never copy a secret, signed URL, message body, verification token, connection URL or raw provider
response into the incident record.

## Named rollback point

The named pre-OPS-003 application/Edge rollback point is commit `d2b7bf3`. For every later release,
the release record must name the immediately previous known-good immutable commit and the matching
API, web and Edge deployment identifiers. A code rollback is allowed only while the database schema
is compatible. The OPS-003 observability commit itself is additive and creates no database revision.

Do not use `git reset --hard`, rewrite `main`, or restore a database over an active environment.
Provider rollback/promote operations must select an existing immutable artifact built from the
recorded commit.

## Deployment rollback runbook

1. Declare the incident, stop further deploys and capture the safe release identifiers.
2. Check liveness/readiness, API 5xx, Cron/Edge/outbox state and current Alembic head. Do not inspect
   payloads to decide rollback.
3. Decide schema compatibility with the migration recovery decision tree below. If unknown, keep
   traffic in maintenance/fail-closed mode and do not roll code backward.
4. For the API, redeploy/promote the last known-good artifact. For the web, use Vercel's immutable
   previous deployment. For the Edge Function, deploy the reviewed directory from the named commit.
   Do not alter its six secrets during an ordinary code rollback.
5. Leave the one-minute Cron job enabled only when the deployed Edge Function is healthy. Never run
   the Python worker in parallel.
6. Prove `/api/health/live`, `/api/health/ready`, trusted/negative WSS probes, one empty-queue Cron
   call and the affected API smoke. Observe for at least 10 minutes.
7. Record result, owner and follow-up. Roll forward with a reviewed fix; do not patch provider state
   without capturing the change.

## DB migration recovery decision tree

```text
Migration reports failure
├─ Did the application revision remain at the old head and no DDL commit?
│  ├─ Yes: keep old code, fix the migration, rehearse on a disposable restore, retry.
│  └─ No: continue.
├─ Is the new schema complete and backward-compatible with the old code?
│  ├─ Yes: roll application code back if needed; preserve schema; repair/roll forward migration.
│  └─ No: continue.
├─ Is a reviewed Alembic downgrade proven lossless on the disposable restored backup?
│  ├─ Yes: stop writes, take another forensic backup, run the reviewed downgrade, verify, reopen.
│  └─ No: continue.
└─ Keep writes stopped; create a new isolated database from the verified pre-migration backup,
   validate counts/checksums/revision, switch only through the approved cutover, then preserve the
   failed database for investigation.
```

Rules for every branch:

- Never use `alembic stamp` to hide a partially applied migration. Stamp is allowed only after an
  owner proves the physical schema already matches the exact revision on a disposable copy.
- Never edit `alembic_version` directly, improvise reverse SQL, or downgrade production before the
  same path succeeds against a disposable restore.
- Take a new backup before any recovery mutation. Verify byte size, checksum, inventory and restore
  target; provider-managed schemas are preserved rather than blindly overwritten.
- Runtime credentials cannot execute migration DDL. Only the separated migration credential may run
  reviewed Alembic operations.

## Email outage recovery

1. Detect the outage from Edge 5xx/retry counts, terminal outbox count, oldest-ready age, safe error
   codes and provider status/quota. The originating application transaction remains committed.
2. If Resend is transiently unavailable, leave Cron running so bounded 1/2/4/8-minute retries and
   five-minute lease recovery operate normally. Do not hot-loop or increase batch/concurrency.
3. For authentication/domain/quota failure, prevent a burst, repair or rotate the credential/domain
   in the approved secret store, then make one authenticated empty-queue/manual canary and observe
   one scheduled HTTP 200. No paid plan is authorized automatically.
4. Before manually requeuing terminal rows, disable the named Cron job and wait for active leases to
   finish or expire. Review only IDs, state/times, attempts and safe error codes. Never display
   recipient, payload, idempotency key or provider ID.
5. If the outage remained inside Resend's 24-hour idempotency window, a reviewed operator transaction
   may clear the terminal state and schedule the selected IDs for retry while preserving their
   existing keys. If the acknowledgement gap may exceed 24 hours, stop for product/operations review
   because duplicate delivery is possible; do not claim exactly-once behavior.
6. A manual Python fallback is allowed only for a healthy provider when Cron/Edge itself is the
   failure. Disable/unschedule Cron first, reconcile leases, run one bounded `--once` batch, stop the
   process, reconcile state and only then re-enable Cron. Do not introduce a Google Cloud worker,
   Render Background Worker or hosted Python worker.
7. Recovery is complete after ready/expired-lease/terminal counts return to expected levels and at
   least two scheduled runs succeed without duplicate delivery.

## Redis loss and WSS recovery

Redis outage must fail closed for rate-limited operations and report `redis=unavailable` in
readiness. Confirm the TLS Redis service and quotas, repair connectivity/credential configuration,
then wait for the existing client to reconnect and prove `redis=ok`. Run trusted and unrelated-Origin
WSS probes. When chat exists, clients reconnect and recover committed messages via authorized REST;
do not synthesize Pub/Sub events or read message body content from logs.

## Backup failure recovery

Any backup failure aborts a planned reset. Keep the application write barrier in its previous safe
state; never proceed with deletion based on a partial database dump or avatar copy.

1. Mark the operation FAILED and preserve its safe operation ID plus aggregate failure code.
2. Determine whether the failure is export, upload/copy, inventory, checksum, count, permission,
   capacity or expiry. Do not log object contents, signed URLs or credentials.
3. Remove/quarantine only the incomplete operation prefix after resolving its exact private target;
   never delete a broad bucket/prefix.
4. Repair capacity, private access or credentials through the credential rotation runbook. Create a
   new operation ID; do not mutate a failed manifest into READY.
5. Re-export database data and recopy every required avatar, then independently verify inventory,
   counts, bytes and checksums in a disposable restore.
6. Reset/restore remains forbidden until both artifacts are READY. Any restore mismatch keeps the
   maintenance barrier closed and selects roll-forward repair or an isolated restore from the last
   verified backup; never merge with a new cohort.

## Tabletop/game-day cadence

Run failed-migration, Redis-loss, email-outage and backup-failure exercises on isolated local or
staging resources before destructive Semester work and at least once before production approval.
The evidence must distinguish automated simulation, operator tabletop and live staging action. A
repository test cannot mark provider alert routing PASS.
