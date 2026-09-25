# OPS-002 staging evidence — 2026-09-25

Status: **BLOCKED / IN ACCEPTANCE — READY FOR FREE-WORKER PROVISIONING**. This is partial evidence
for the early staging infrastructure gate; it does not mark OPS-002 complete.

The worker deployment decision was amended on 2026-09-25: a paid Render Background Worker is removed
from the plan. Resend and the PostgreSQL transactional outbox remain. The primary target is the gated
Google Compute Engine `e2-micro` design in the OPS-002 runbook; Oracle Cloud Free Tier audit is the
first fallback when an allowance, IPv6 or egress gate fails.

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
| Backup restore/rollback rehearsal | PASS | Disposable Supabase-compatible project preserved provider-managed schemas, restored every portable application object, migrated to head, downgraded to zero application tables, then restored/re-applied migrations to head. |
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

### Disposable restore rehearsal

- Completed: `2026-09-25T12:49:01Z`
- Disposable project ref: `wxhluiwxholhndlcwyen`
- Connection: Session Pooler port 5432 with `sslmode=require`; client evidence reported TLSv1.3
  with cipher `TLS_AES_256_GCM_SHA384`
- Archive inventory: 527 Supabase-managed entries and zero portable application entries. The fresh
  target's managed schemas were intentionally preserved; no provider-managed object was blindly
  overwritten.
- Pre-migration verification: PostgreSQL 17; `auth`, `storage`, `realtime`, and `extensions`
  present; `app_private` and `alembic_version` absent.
- Safe restore result: PASS. All portable application payload (zero objects for this genuine
  pre-migration baseline) was selected; the clean pre-migration state and four managed schemas were
  unchanged.
- Migration verification: `0009_transactional_outbox`; 14 application tables; representative row
  counts were users 0, interests 13, languages 8, and transactional outbox 0.
- Rollback verification: downgrade to base left zero application tables.
- Recovery verification: safe restore followed by a second upgrade returned to
  `0009_transactional_outbox` with 14 application tables.

The active staging database was not connected to or modified during this rehearsal. The password,
connection string, and raw client output were not persisted.

## Remaining mandatory evidence

- GCP Free Tier/billing allowance and resource-shape preflight, including a project budget alert
  whose evidence notes that it is not a hard spending cap.
- Supabase direct database AAAA plus real PostgreSQL IPv6/TLS with the runtime role, and Resend AAAA
  plus real HTTPS/TLS over IPv6, before any long-running worker deployment.
- A separate GCP staging email worker running an immutable reviewed commit, a delivered Resend
  message, one successful verification, generic replay failure, retry/idempotency and worker
  lease/service/VM restart recovery.
- A 24-hour `vnstat` window with runtime TX `<=25 MiB/day`, plus Google Billing Reports showing no
  unexpected paid resource.
- Authenticated refresh/F5/logout, profile read/update, avatar upload/private authenticated read,
  anonymous denial, and persistence checks.
- Controlled Redis outage showing fail-closed behavior followed by recovery.

These items require a separately authorized free-tier provisioning/acceptance session and remain
blockers. A failed GCP allowance, IPv6 or egress gate stops the GCP path and opens the Oracle Cloud
Free Tier audit; it does not authorize paid infrastructure. No secret, token, cookie value,
verification URL, credential, message body, or raw authorization header is recorded here.
