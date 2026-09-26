# OPS-003 game-day evidence — 2026-09-26

Status: **REPOSITORY/TABLETOP PASS; ACCOUNT ALERT ROUTING BLOCKED**.

This record distinguishes repository automation and tabletop decisions from account-owned staging
actions. It does not claim provider notification delivery, a destructive migration, a live Redis
outage or a Semester backup implementation that was not exercised here.

## Baseline and scope

- Source baseline fetched before implementation: `main` and `origin/main` both at `d2b7bf3`.
- Named pre-OPS-003 rollback point: `d2b7bf3`.
- Scope: API/Edge redacted logs, safe Cron/outbox monitoring, rollback/recovery/rotation documents
  and failure exercises only.
- Email topology remained Backend → transactional outbox → Supabase Cron → Edge Function → Resend.
- No account setting, secret, provider route, database, Redis instance or hosted worker was changed.

## Automated gates

| Gate | Result | Evidence |
|---|---|---|
| Backend full suite | PASS | `799 passed, 19 environment-gated live tests skipped` in 26.85 seconds. |
| OPS-003 focused suite | PASS | 28 tests covering API log redaction, monitoring/runbook contracts, readiness, outbox and fallback CLI. |
| Regression files affected by exception flow | PASS | 50 tests across observability, Admin/profile/catalog/completion APIs. |
| Ruff | PASS | `ruff check app alembic tests`. |
| Mypy strict | PASS | `mypy app alembic tests`; 150 source files. |
| Edge core | PASS | Node 24 executed 7 TypeScript tests: structured log redaction and acceptance A–F. |
| Alembic graph | PASS | Single head `0010_edge_email_outbox_functions`; history is linear through `0001..0010`. |
| Diff/secret pattern gate | PASS | `git diff --check`; targeted credential/URL/bearer-key scan returned no match. |

The host had no Deno executable. The Edge core is platform-neutral and was executed directly by
Node 24; the deployed Deno entrypoint was not invoked because doing so requires account secrets.
This limitation is not represented as a live Edge PASS; OPS-002 already records the deployed worker
acceptance before this log-only change.

## Game-day scenarios

### Failed migration — TABLETOP PASS

The exercise began at the recorded rollback point with a verified linear Alembic graph. The decision
tree chose: keep writes stopped; determine physical revision/DDL commit; use old code only when the
schema is backward-compatible; rehearse any downgrade against a disposable restored backup; otherwise
restore into a new isolated database and cut over after counts/checksums pass. Direct edits to
`alembic_version`, unproven `stamp`, reverse SQL and overwrite of active staging were rejected.

No migration was deliberately failed against staging. This is a repository tabletop backed by the
graph gate and the prior OPS-002 disposable restore rehearsal.

### Redis loss — AUTOMATED PASS / LIVE NOT REPEATED

The readiness test injected a Redis error, observed only `unavailable`, then recovered to `ok` on the
next successful probe. The full suite also retained fail-closed rate-limit and TLS configuration
coverage. The response/log contract did not expose endpoint or credential diagnostics. OPS-002
already records the controlled staging outage/recovery, so it was not repeated during this code task.

### Email outage — AUTOMATED PASS

The Edge core retry test injected a retryable provider HTTP failure, released the lease, preserved the
stable idempotency key and succeeded on the later execution. Python outbox tests and the fallback CLI
contract also passed. The tabletop kept Cron running for transient provider failure and allowed the
Python fallback only after Cron is disabled and leases reconcile. A delay beyond the provider's
idempotency-retention window requires operator review because duplicate delivery is possible.

### Backup failure — TABLETOP PASS; IMPLEMENTATION DEFERRED TO SEM

The exercise treated export, avatar copy, inventory, checksum or count mismatch as FAILED and aborted
reset. It kept the write/maintenance barrier safe, quarantined only the exact incomplete operation,
required a new operation ID and demanded a disposable restore before READY. It rejected partial
backup, broad bucket deletion, signed URL logging and merge/overwrite of a new cohort.

SEM-002/003 backup adapters do not exist yet, so no fake database/avatar failure was injected. The
fail-closed recovery procedure and repository contract test pass; live fault injection remains a
mandatory SEM/ACCEPT staging gate.

## Alert routing gate

Result: **BLOCKED — ACCOUNT OWNER ACTION REQUIRED**.

Repository tests cannot prove delivery to real primary and backup Operations routes. The account
owner must send provider test notifications or safe staging synthetic alerts for API 5xx,
Cron/Edge failure and backup failure; both roles must receive and acknowledge. Record only UTC time,
alert name, role, PASS/FAIL and acknowledgement latency. Do not record recipient addresses, webhook
URLs, account identifiers or tokens. OPS-003 must not be marked DONE until this evidence is added.

## Security review

- Logs and monitoring use fixed aggregate fields only.
- No verification token/link, signed URL, recipient, message body, payload, idempotency key,
  provider ID, database/Redis URL, API key, password, cookie or authorization header was recorded.
- No populated `.env` is part of the intended change set.
- The final staged diff and tracked-file secret scan remain required immediately before commit.
