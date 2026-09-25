# OPS-002 staging evidence — 2026-09-25

Status: **BLOCKED**. This is partial evidence for the early staging infrastructure gate; it does
not mark OPS-002 complete.

## Deployment under test

- Evidence timestamp: `2026-09-25T08:29:49Z`
- Tested application commit: `71504437c05a6a11624d367d5a39da6509e371dd`
- Frontend: `https://staging.vgubuddyprogram.com` (Vercel, `main`, `apps/web`)
- API: `https://api.staging.vgubuddyprogram.com` (Render service
  `vgu-buddy-api-staging`, Singapore, `main`, `apps/api`)
- PostgreSQL/Storage: isolated Supabase project `vgu-buddy-staging`, Singapore; private
  `profile-images` bucket
- Redis: isolated TLS Upstash database `vgu-buddy-staging`, Singapore
- Email sender: Resend with verified staging sending domain
- Reported migration head: `0009_transactional_outbox`

No production resource or data was used.

## Verified evidence

| Gate | Result | Sanitized evidence |
|---|---|---|
| Frontend HTTPS | PASS | Staging page loaded over the custom HTTPS origin. |
| SPA deep links | PASS | Direct `/login`, `/register`, `/verify-email`, and `/user/profile` navigation reached the SPA; the protected profile route redirected to login without a session. |
| API liveness/readiness | PASS | Public HTTPS health checks passed; readiness reported database and Redis `ok`, and email and storage `configured`. |
| Exact CORS | PASS | The staging frontend Origin was allowed with credentials; an unrelated Origin received no allow-origin response. |
| Secure CSRF cookie | PASS | Cookie attributes included `Secure`, `HttpOnly`, `SameSite=Lax`, host-only naming, and `Path=/`; no cookie value was recorded. |
| WSS trusted Origin | PASS | `/api/health/ws` accepted the exact staging frontend Origin and returned the fixed liveness payload. |
| WSS unrelated Origin | PASS | `/api/health/ws` rejected an unrelated Origin during handshake. |
| Trusted proxy policy | PASS | Deployed image configuration enables proxy headers only for loopback (`127.0.0.1`), not a wildcard. |
| Local focused backend tests | PASS | Infrastructure-health and local-TLS tests: 7 passed. Ruff and mypy passed for affected backend code. |
| Local focused frontend tests | PASS | API URL/proxy tests: 13 passed. |
| Container/config gate | PASS | API Docker image built with the audited command; Compose configuration validation passed. |

Registration/login and the student password policy were confirmed against staging before this
evidence run. The remaining authenticated flows below require a controlled staging account and are
not promoted to PASS by that earlier smoke.

## Backup artifact

- File: `pre_ops002_2026-09-25.dump` (stored outside the repository)
- Format: PostgreSQL custom archive
- Size: `354113` bytes
- SHA-256: `ADF0ABBAED0FFEFFAD20A48B6315E74490726638E412C2E61FFA645A8DDA1980`
- Structural check: `pg_restore --list` succeeded; 560 TOC entries
- State: created before the application migration and contains Supabase-managed schemas, roles,
  and extensions. A restore into ordinary PostgreSQL would not satisfy the gate.

The active staging database was not modified. A full restore and migration rehearsal remains
pending on a separate disposable Supabase-compatible target.

## Remaining mandatory evidence

- A separate staging email worker, a delivered Resend message, one successful verification, generic
  replay failure, and worker lease/restart recovery.
- Authenticated refresh/F5/logout, profile read/update, avatar upload/private authenticated read,
  anonymous denial, and persistence checks.
- Controlled Redis outage showing fail-closed behavior followed by recovery.
- Full backup restore into a disposable Supabase-compatible target, verification of the restored
  pre-migration state, migration to head, and rollback/recovery decision evidence.

These items require external service access or an explicitly approved paid worker and remain
blockers. No secret, token, cookie value, verification URL, credential, message body, or raw
authorization header is recorded here.
