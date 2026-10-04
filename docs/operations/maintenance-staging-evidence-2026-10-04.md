# Maintenance scheduler staging evidence — 2026-10-04

## Result

**PASS — staging Maintenance Scheduler accepted.** The accepted candidate is commit `5b20c00` and
the deployed path is `POST /api/internal/maintenance` on the existing staging API. This record
contains no secret, Vault value, response header, object key, user identity or maintenance payload.

## Evidence

The operator confirmed all of the following after configuring the dedicated Render secret and the
two staging Supabase Vault entries, then running the committed Cron SQL:

- `maintenance-worker-health.sql` showed successful Cron execution after at least two complete
  15-minute schedule intervals;
- Render logs contained `invitation_expiry_batch_completed`;
- Render logs contained `chat_message_cleanup_batch_completed`;
- Render logs contained `semester_backup_expiry_batch_completed`.

This combination is authoritative for execution: Supabase Cron success proves the `pg_net` request
was enqueued, while the three sanitized API completion events prove all three bounded maintenance
services actually ran. No event body, aggregate count or provider response was copied into this
record because it was not needed to establish completion.

The repository operator then independently rechecked the public staging boundary without using the
secret:

| Check | Result |
| --- | --- |
| `GET /api/health/live` | HTTP 200 |
| `GET /api/health/ready` | HTTP 200 |
| unauthenticated `POST /api/internal/maintenance` | HTTP 401 with only `{"error":"unauthorized"}` |

Before the manual configuration, the same unauthenticated POST returned the generic configuration
503. The later 401 therefore also confirms the deployed process loaded the dedicated maintenance
configuration while continuing to reject unauthenticated execution.

## Security and scope conclusion

- Cron uses the committed `cron.schedule`/Vault/`pg_net` path; no direct mutation of `cron.job` and
  no GitHub Actions scheduler were introduced.
- The API secret comparison remains constant-time, and local tests prove missing and incorrect
  secrets do not invoke the worker.
- The API response and logs expose aggregate outcomes only. Database, Storage, Redis and auth
  credentials remain outside the Cron SQL and repository.
- Invitation expiry, chat retention cleanup and semester-backup expiry are all covered by staging
  provider evidence.

The staging maintenance blocker is closed. Production must create its own Render secret, Supabase
Vault entries and Cron job during isolated production provisioning; this staging secret and these
Vault entries must never be copied into production.
