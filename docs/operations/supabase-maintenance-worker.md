# Supabase scheduled maintenance worker

Production retention uses one provider-neutral, bounded API call:

```text
Supabase Cron (every 15 minutes)
    -> POST /api/internal/maintenance
    -> expire invitations (maximum 100)
    -> delete expired chat messages (maximum 100)
    -> expire/delete semester backup artifacts (maximum 100)
```

The endpoint calls the existing Python services. It does not duplicate their SQL, widen database
permissions, or put database and Storage credentials in an Edge Function or GitHub Actions. Each
service retains its own short transaction and idempotent retry boundary. A failed pass returns 503;
the next scheduled pass retries remaining work.

## Security boundary

- `MAINTENANCE_WORKER_CRON_SECRET` is a dedicated random value of at least 32 bytes. It is not an
  auth/CSRF/JWT key and must not be reused.
- The API compares the `x-cron-secret` header in constant time. The private route is omitted from
  OpenAPI, accepts POST only, returns aggregate counts only, and sends `Cache-Control: no-store`.
- Supabase Vault stores only the full HTTPS endpoint and the Cron secret. It never stores the API's
  database URL, Storage key, Redis URL, or application auth keys.
- The backend provider's secret store holds the matching Cron secret. Do not put it in Vercel,
  source, a command argument, an issue, chat, CI output, or an acceptance record.
- This is server-to-server authentication, so the browser CSRF token is deliberately not used.
  CORS does not allow the private header to browser callers.

## Deployment order

Do not schedule the job until the new endpoint is deployed and healthy.

1. Generate one high-entropy secret without printing it. On PowerShell, these commands leave the
   value out of command history:

   ```powershell
   $maintenanceBytes = [byte[]]::new(48)
   [Security.Cryptography.RandomNumberGenerator]::Fill($maintenanceBytes)
   $maintenanceSecret = [Convert]::ToBase64String($maintenanceBytes)
   Set-Clipboard -Value $maintenanceSecret
   ```

2. In the selected API provider's server-only secret store, create
   `MAINTENANCE_WORKER_CRON_SECRET` from the clipboard. Never expose the value to the frontend.
3. Deploy the reviewed API revision. Confirm liveness/readiness and confirm an unauthenticated POST
   to `/api/internal/maintenance` returns the generic 401 response. Do not include the secret in a
   shell command or screenshot.
4. In **Supabase Dashboard -> Project Settings -> Vault**, create:
   - `buddy_maintenance_api_url`: the full first-party HTTPS URL ending in
     `/api/internal/maintenance`;
   - `buddy_maintenance_cron_secret`: exactly the same value as the backend setting.
5. In **Supabase Dashboard -> Integrations -> Cron**, confirm Cron is enabled. Enable `pg_net` only
   if the integration reports it unavailable.
6. In **SQL Editor**, run `supabase/cron/maintenance-worker.sql`. The case-sensitive job name is
   `vgu-buddy-maintenance-every-15-minutes`; rerunning the file updates that job instead of creating
   a second scheduler.
7. Clear the local variable and clipboard:

   ```powershell
   $maintenanceSecret = $null
   [Array]::Clear($maintenanceBytes, 0, $maintenanceBytes.Length)
   Set-Clipboard -Value ''
   ```

No step above authorizes a paid plan, a new database, or a second scheduler.

## Acceptance and monitoring

Record only UTC time, deployment revision, job name, status, duration, and aggregate counts.

1. Invoke one authenticated empty/due-work pass through a client that accepts a secret via a
   secure prompt or header file. Do not put the header value in a command line.
2. Confirm HTTP 200 and the three bounded aggregate reports. If more than 100 rows are due, confirm
   later passes drain the backlog without increasing the batch.
3. Confirm a wrong or missing secret returns 401 and no maintenance service runs.
4. Confirm one scheduled run succeeds, then inspect the read-only
   `supabase/monitoring/maintenance-worker-health.sql` snapshot.
5. Confirm API structured logs contain the three sanitized completion events and no object key,
   URL, credential, email, message body, or student identity.
6. Recheck after at least two schedule intervals. A 503 or failed Cron run is an alert; it is not a
   reason to start a concurrent ad-hoc loop.

A `succeeded` row in `cron.job_run_details` proves that Cron enqueued the `pg_net` request, not that
the remote API returned 2xx. The corresponding sanitized API completion events are the
authoritative execution signal; use Supabase's HTTP-response diagnostics only without selecting
response bodies, headers, URLs, or Vault values.

Cron and `pg_net` are available on Supabase's hosted platform, but quotas and availability can
change. Recheck the current [Cron documentation](https://supabase.com/docs/guides/cron) before the
production cutover.

## Disable, rotate, and recover

Disable without deleting application data:

```sql
SELECT cron.unschedule('vgu-buddy-maintenance-every-15-minutes');
```

To rotate, unschedule first, wait for an active call to finish, replace the backend secret and
Vault secret together, make one secure manual canary, then rerun the committed schedule file.
Delete the old Vault secret only after the new call succeeds. Never run two differently configured
jobs in parallel.

Invitation reads already project stale PENDING rows as expired, and chat reads exclude expired
messages, so a short scheduler outage preserves authorization semantics. Physical cleanup and
backup-object expiry remain delayed until the worker recovers. Any semester backup cleanup failure
must be investigated under the existing backup failure runbook; never delete a broad bucket or
prefix manually.
