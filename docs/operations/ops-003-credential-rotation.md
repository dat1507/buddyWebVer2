# OPS-003 credential rotation procedure

Credential rotation is a controlled deployment, not an incident-log copy of secret values. Use the
provider's server-side secret store or a hidden prompt. Never pass a value in chat, Git, command-line
arguments, screenshots or evidence. Never log a database URL, API key, password, cookie,
verification token, signed URL or message body.

## Common procedure

1. Declare scope, environment, owner, reason and UTC start. Inventory consumers by variable name
   only; verify a current backup and rollback point.
2. Create a new value in the authoritative provider. Prefer overlapping old/new validity where the
   credential type supports it. Do not revoke the old value first unless compromise requires it.
3. Update server-only consumers, redeploy/restart, and run the smallest safe canary plus readiness.
4. Confirm old/new deployment convergence and monitoring. Revoke the old value, then prove the old
   value no longer works without printing it.
5. Record variable name, systems updated, timestamps, owner, canary result and revocation result—no
   value, fingerprint derived from the value, endpoint credential or private recipient.

Compromise overrides convenience: contain access, preserve redacted audit evidence, rotate all
potentially shared/derived credentials, invalidate affected sessions/tokens, and notify the security
owner. Do not wait for a maintenance window.

## Rotation matrix and ordering

| Credential | Consumers | Required order / impact |
|---|---|---|
| Runtime DB password/URL | FastAPI and Edge `OUTBOX_DATABASE_URL` | Create/alter least-privilege role secret, update both consumers, canary API + empty worker, then revoke old login/password. Never use migration owner. |
| Migration DB credential | Alembic operator/CI only | Rotate separately; prove `current`/dry migration connection and confirm runtime still cannot DDL. |
| Redis URL/password | API/rate limit, later WSS/PubSub | Update server secret, restart, prove readiness outage→recovery and TLS; revoke old credential. |
| Resend API key | Edge and local/manual fallback config | Create new key, update Edge and approved fallback store, send one designated staging canary, revoke old key. Do not rotate sender/domain casually. |
| Cron secret | Edge `EMAIL_WORKER_CRON_SECRET` and Vault `buddy_email_worker_cron_secret` | Disable Cron, wait/reconcile leases, update both locations, manual authenticated empty-queue call, re-enable one job and prove HTTP 200. Never run Python during the gap. |
| Verification sealing key | API enqueue and Edge decrypt | Planned: drain ready/retry/leased verification jobs, disable Cron, update both consumers together, request a new canary, re-enable. Compromise: invalidate outstanding verification tokens/outbox events and reissue under the new key; old sealed payloads must not be silently retried. |
| JWT signing secret | FastAPI | Update/redeploy and intentionally invalidate all sessions; users must log in again. Verify generic rejection of old cookies. |
| CSRF secret | FastAPI | Update with the auth deployment; existing CSRF values fail and clients reload/re-authenticate. Never reuse the JWT key. |
| Supabase Storage secret key | FastAPI Storage service | Create/rotate provider key, update API, test private authenticated avatar read and anonymous denial, revoke old key. Never expose it to browser variables. |

## Email credential rotation details

For the Resend key, keep the current transactional outbox rows unchanged. Provider idempotency keys
are data identifiers, not credentials, and are not rewritten. If the old provider key may have been
used by an attacker, inspect provider audit/delivery aggregates without copying recipients or body
content, revoke immediately and treat unexpected delivery as a security incident.

The verification sealing key is not interchangeable with the JWT/CSRF/Cron secrets. A planned
rotation must avoid leaving rows encrypted only with the old key. If the queue cannot drain, deploy a
reviewed versioned dual-decrypt transition before rotation; this requires a separate security-reviewed
change and is not improvised during OPS-003. After suspected compromise, correctness favors
superseding/reissuing verification requests over preserving old links.

## Rotation acceptance

Pass requires healthy API readiness, one successful scheduled Edge invocation, expected outbox
state, Redis readiness, private Storage access control and explicit old-credential revocation. The
alert routing test must reach primary and backup operators. Record only redacted PASS/FAIL evidence.
