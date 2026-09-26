# OPS-003 observability and alerting runbook

This runbook covers the deployed API and the existing transactional email path:

```text
FastAPI -> app_private.transactional_outbox -> Supabase Cron -> Edge Function -> Resend
```

It does not introduce another scheduler. The hosted Python worker remains disabled unless the
email recovery procedure explicitly activates it after Cron is disabled.

## Telemetry data policy

Operational telemetry is an allowlist, not a copy of application data. Never record or attach:

- credentials, API keys, cookies, authorization headers or database/Redis URLs;
- verification tokens, sealed verification payloads or verification links;
- signed URL values, email addresses, recipient fields or provider response bodies;
- request/query bodies, invitation/chat message body content, profile free text or uploaded bytes;
- outbox payload, idempotency key, lease owner or provider message ID.

Dashboard access is least-privilege: read-only Operations access for aggregate health, separate
audited database access for the monitoring SQL, and no broad provider/account-admin role merely to
view alerts. Retain operational logs for the shortest provider-supported period needed for incident
response; the initial target is 14 days, reviewed before production.

## Structured redacted logs

FastAPI emits one JSON line named `api_request_completed` per handled HTTP request. Its entire
allowlist is `timestamp`, `service`, `event`, server-generated `request_id`, `method`, route template,
`status_code`, `duration_ms` and optional exception class `error_type`. It never logs a raw path,
query, request/response body or header. The response exposes `X-Request-ID` so an operator can find
the corresponding event without learning private input. A 4xx is warning level and a 5xx is error
level. Unhandled API failure responses are generic and no-store.

The Edge Function emits one JSON line named `email_worker_invocation_completed`. Its allowlist is
`timestamp`, `level`, `service`, `event`, random `invocation_id`, status/duration, a controlled
outcome and the aggregate `claimed`, `sent`, `retry_scheduled`, `terminal_failed` and `skipped`
counts when available. It never logs job rows or delivery inputs.

Do not enable framework/database debug or SQL parameter logging in staging or production. If a
temporary diagnostic needs more fields, review the field allowlist and remove the change after the
incident; never print an exception message whose origin may contain a connection URL.

## Signals, thresholds and response

Thresholds are initial operating values for the current one-minute schedule. Tune them from
measured staging traffic without weakening the hard failure alerts.

| Signal | Alert | Severity | First response |
|---|---|---:|---|
| API liveness | Two failed probes in 2 minutes | Critical | Check deploy/runtime; rollback code only if DB-compatible. |
| API readiness | Two 503 probes in 2 minutes | High | Use fixed dependency states to isolate DB, Redis, email config or Storage. |
| API failure | Any 5xx burst of 5 in 5 minutes, or >2% with at least 20 requests | High | Correlate by route template/request ID; never search by token or body. |
| API latency | p95 >2 seconds for 10 minutes | Medium | Check host/DB/Redis saturation and recent deploy. |
| Cron | No successful named run for 3 minutes, or any failed run | High | Inspect sanitized run status and Edge status; do not start Python concurrently. |
| Edge Function | Any 5xx, terminal failure, or p95 runtime >120 seconds | High | Check configuration/provider/outbox state and quota. |
| Outbox | Oldest ready row >5 minutes or any lease expired >2 minutes | High | Confirm Cron/Edge activity; reconcile leases before fallback. |
| Outbox | Any `terminal_failed` row | High | Group by safe error code; follow email outage recovery. |
| Resend | Daily/monthly usage reaches 80%; provider 429/auth/5xx | High | Pause onboarding burst or repair key/domain; no automatic paid upgrade. |
| Redis | Readiness says unavailable twice in 2 minutes | High | Fail closed, recover TLS service, then verify readiness. |
| WSS | Trusted-Origin synthetic handshake fails twice; unrelated Origin is accepted once | High/Critical | Check upgrade/origin config; an accepted unrelated Origin is a security incident. |
| Backup failure | Backup state FAILED, missing object, checksum/count mismatch or expiry <72h before a planned reset | Critical | Abort reset/restore and follow backup failure recovery. |
| Restore | Any checksum/count/referential mismatch | Critical | Keep maintenance barrier closed; never merge or overwrite a new cohort. |

Use [email-worker-health.sql](../../supabase/monitoring/email-worker-health.sql) for a read-only
Cron/outbox snapshot. The result contains only timestamps, aggregate counts and safe error codes.
Do not replace it with `SELECT *` or add restricted columns. Edge invocation status/runtime comes
from the Supabase Function dashboard, and provider quota/delivery status comes from Resend using
operator-only access.

## Redis and WSS monitoring strategy

Current repository monitoring uses `/api/health/ready` for a real Redis `PING` and
`/api/health/ws` for an exact-Origin WebSocket upgrade probe. Run the trusted-Origin probe from the
same region as the frontend and a negative probe with a fixed unrelated test Origin. Store only
result, status/close code, duration and UTC time—never cookies or the WebSocket URL query.

When CHAT-003 later supplies realtime chat, add aggregate connection/open/close counts, handshake
denials by safe reason, publish failure count, reconnect rate and REST catch-up success. PostgreSQL
remains message truth. Redis loss must not lose committed data; it should disable realtime delivery,
raise an alert and recover through reconnect plus authorized REST history. This OPS task does not
implement CHAT or inspect message bodies.

## Backup/restore monitoring strategy

Before SEM backup/reset code exists, monitor the last verified database backup/rehearsal record and
any private Storage backup job supplied by the provider. Once SEM-002..004 exist, require these
aggregate fields for every operation: operation ID, state, started/completed time, object/row counts,
total bytes, manifest checksum result and expiry. Never place a signed URL, object content, database
URL or credential in telemetry.

A reset cannot start unless both database and avatar backup states are READY and independently
verified. Any backup failure, missing/corrupt object, count/checksum mismatch or expired artifact is
fail-closed and pages the operator. A restore remains under the maintenance barrier until all counts,
checksums and required references reconcile.

## Alert routing and account-specific acceptance gate

Route Critical/High alerts to the primary Operations on-call and a distinct backup operator; route
security-origin failures to the security owner as well. Medium alerts may use the Operations queue.
The roles, acknowledgement time and escalation path belong in the private provider configuration,
not Git.

Alert routing verification is account-specific and cannot be satisfied by repository tests. An
account owner must use the provider's test-notification feature (or a non-production synthetic alert)
for API 5xx, Cron/Edge failure and backup failure, then record only UTC time, alert name, route role,
delivery result and acknowledgement latency in the OPS-003 evidence file. Do not record recipient
addresses, webhook URLs or integration tokens. OPS-003 remains blocked until primary and backup
routing both receive and acknowledge the test.
