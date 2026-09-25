# OPS-002 staging validation runbook

This is an early infrastructure gate, not a product release. Use only isolated staging resources;
never point these steps at production data, domains, credentials, email recipients, or storage.

## Required topology

- Frontend: the existing Vercel project at `https://staging.vgubuddyprogram.com`, with Root
  Directory `apps/web`, HTTPS enabled, SPA rewrites active, `VITE_EVENT_SLIDER_USE_MOCKS=false`, and
  `VITE_API_URL=https://api.staging.vgubuddyprogram.com/api`.
- API: the existing Render Web Service `vgu-buddy-api-staging` at
  `https://api.staging.vgubuddyprogram.com` using the committed API image. It must remain
  WebSocket-capable. Frontend and API are subdomains of the same registrable site.
- Worker: a separately running instance of `python -m app.cli email-worker` on a dedicated Google
  Compute Engine Free Tier candidate. It must not run inside the request process or share its VM
  with FastAPI, frontend, PostgreSQL or Redis.
- Database: the isolated Supabase project `vgu-buddy-staging` with a least-privilege runtime URL and
  a distinct migration URL. The local-only runtime-role bootstrap command must not be used in
  staging.
- Redis: the isolated Upstash database `vgu-buddy-staging` using a credentialed `rediss://` URL and
  staging-only `REDIS_KEY_PREFIX` and
  `RATE_LIMIT_KEY_PREFIX` values containing `:production:` when `APP_ENV=production`.
- Storage and email: the private Supabase `profile-images` bucket and the verified Resend sender on
  `mail.staging.vgubuddyprogram.com`. Server keys belong only in the API/worker secret stores.

Vercel preview/production environment variables must contain only browser-safe `VITE_*` values.
Keep `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` in the CI secret store if CLI deploys
are used; never commit `.vercel` or token values. Build before deploy and deploy the tested prebuilt
artifact. Git-integrated deployment is also acceptable when it preserves the same gate order.

The Render Free Web Service may cold-start after idle for this early staging gate because it remains
a WebSocket-capable persistent-process host once awake; warm it before timed smoke checks and record
the cold start. It is not an always-on production SLO. A sleeping or second Web Service must not be
used to impersonate the required worker. A paid Render Background Worker is removed from this plan
and is not a staging or production dependency.

## Free-worker decision and ordered gates

The primary worker target is:

| Setting | Required value |
|---|---|
| Provider | Google Cloud Compute Engine |
| Region / zone | `us-west1` / `us-west1-b` |
| Machine / provisioning | `e2-micro`, STANDARD/non-preemptible |
| OS | Ubuntu 24.04 LTS x86-64 |
| Boot disk | 30 GB `pd-standard` |
| Accelerators/storage | No GPU, TPU or Local SSD |
| Public networking | No external IPv4; ephemeral external IPv6 |
| Paid networking/services | No Cloud NAT, load balancer or managed GCP database |

Run the gates in this order and stop on the first failure:

```text
GCP Free Tier allowance
    -> Supabase direct PostgreSQL IPv6 + TLS
    -> Resend HTTPS IPv6 + TLS
    -> provision isolated worker
    -> functional email acceptance
    -> service/VM restart acceptance
    -> 24-hour TX and Billing Report acceptance
```

Before provisioning, confirm that the Cloud Billing account is active, the current Free Tier terms
cover the selected resources/region, no other VM consumes the applicable `e2-micro` allowance, and
total `pd-standard` remains within the current allowance. Configure no snapshot schedule, external
IPv4, Cloud NAT, GPU/TPU or automatic paid add-on. Create a project-specific budget alert and record
that a budget alert is not a hard spending cap. The only approved cost description is: **expected
`$0/month` while remaining inside Free Tier limits and passing all gates**. Never claim guaranteed
zero cost.

At provision time, require an AAAA record and a real PostgreSQL-over-IPv6 TLS connection to
`db.<project-ref>.supabase.co:5432`. Use only the existing least-privilege runtime role such as
`vgu_buddy_runtime`; do not use an IPv4-only pooler, IPv4 add-on or migration/admin credential.
Separately require an AAAA record for `api.resend.com` and a real HTTPS/TLS request over IPv6. A DNS
record alone is insufficient evidence. If either path fails, stop: do not add external IPv4, Cloud
NAT, a paid proxy, paid worker or paid network resource. Mark GCP blocked and audit Oracle Cloud Free
Tier first; do not provision Oracle automatically. If both free approaches fail, open a new explicit
owner decision with technical reason, monthly cost, alternatives and trade-offs.

The current worker idle poll default is 5 seconds. Do not change it in this deployment-planning
task. During acceptance, compare 5 seconds with 15 and 30 seconds using focused lease/retry/
idempotency/concurrency tests, verification and matching-email latency, and measured traffic. Adopt
a longer interval only in a separately reviewed code/config change when all contracts remain safe.

## GCP worker security and systemd baseline

- Code: `/opt/vgu-buddy`; virtualenv: `/opt/vgu-buddy/apps/api/.venv`.
- Runtime user: `vgu-worker` with `/usr/sbin/nologin`.
- Code and virtualenv owner: `root`; deploy an immutable reviewed commit.
- Secret file: `/etc/vgu-buddy/email-worker.env`, owner `root:root`, mode `0600`; enter values with
  a safe direct-server method such as `sudoedit`.
- Command: `python -m app.cli email-worker`.
- Never commit secrets or place them in startup metadata, command-line arguments, shell history,
  terminal output or evidence.
- Use a custom dual-stack VPC/subnet when required; deny inbound IPv6 by default; open no HTTP or
  HTTPS listener; administer through IAP/internal IPv4 with OS Login and least privilege.
- Do not attach the Compute Engine default service account when the worker needs no Google API.
- Use local journald with an explicit size limit. Do not install Cloud Logging/Ops Agent without a
  separately approved operational need and cost review.
- Test application file-write compatibility before enabling `ProtectSystem=strict`. Record any
  incompatibility; do not silently remove hardening.

## Backend security configuration

Set these values in the backend provider's server-only secret store, never in Vercel build variables:

- `APP_ENV=production`
- exact `CORS_ALLOWED_ORIGINS=https://<staging-frontend>`
- `AUTH_COOKIE_SECURE=true`
- exact `PUBLIC_APP_BASE_URL=https://<staging-frontend>`
- independent JWT, CSRF, and email-sealing keys
- staging-only database, `rediss://`, Storage, and email credentials

Never set Uvicorn `--forwarded-allow-ips=*`. Render does not publish a stable ingress proxy CIDR list
for this service contract, so the staging default remains fail-closed: Uvicorn trusts only its
loopback default (`127.0.0.1`) and the application never reads client-supplied forwarding headers
directly. If the provider later documents a narrower peer CIDR, record and regression-test it before
adding it. Until then, an untrusted proxy peer remains the rate-limit identity instead of allowing a
caller to spoof its client address.

## Migration and rollback gate

1. Capture the provider's pre-migration staging backup identifier and retention time. Supabase Free
   projects have no managed daily backup entitlement, so a timestamped off-site logical
   `supabase db dump`/`pg_dump` artifact with byte size and SHA-256 is the accepted identifier for
   this staging gate; never invent a managed-backup identifier.
2. Restore that backup into a separate disposable Supabase-compatible PostgreSQL target and verify
   the expected pre-migration state, then run migrations to head and record representative app
   schema row counts/checksums. A full Supabase dump contains managed schemas, roles and extensions,
   so a partial restore into ordinary PostgreSQL is not evidence for this gate. Never restore over
   the active staging database for this test. On a newly provisioned Supabase target, inventory the
   archive first and preserve the platform-provisioned managed schemas instead of overwriting them;
   restore every portable application-owned object. A genuine pre-migration baseline may contain
   zero portable application objects. In that case, record the zero-object inventory, verify the
   clean baseline and managed schemas, and prove recovery by migrating to head, downgrading, and
   restoring/re-applying migrations on that disposable target.
3. Run `python -m alembic -c pyproject.toml upgrade head` with only the migration credential.
4. Start API and worker with only the runtime credential; confirm the runtime role cannot perform
   migration-owner DDL.
5. Record the tested application rollback artifact and the database recovery decision. A code
   rollback is allowed only while its schema remains compatible; otherwise restore the disposable
   backup and rehearse the documented recovery path.

## Smoke gate

Record UTC timestamp, commit, deployment URLs, resource identifiers, and pass/fail without copying
tokens, cookies, signed URLs, email addresses, or provider response bodies.

- `GET /api/health/live` returns 200.
- `GET /api/health/ready` returns 200 with database/Redis `ok` and email/Storage `configured`.
- `wss://<api-host>/api/health/ws` upgrades from the exact frontend Origin, emits
  `{"status":"alive"}`, and rejects an unrelated Origin.
- Vercel deep links `/login`, `/register`, `/verify-email`, and one protected route load directly.
- Registration, login, refresh/F5, logout, and profile read/update work across the real HTTPS origins.
- Avatar upload/read uses a private bucket and a short-lived signed URL; anonymous object access is
  denied.
- A verification request reaches only the designated staging mailbox, the HTTPS link opens the
  deployed `/verify-email` route, confirmation succeeds once, and replay fails generically.
- Stop/restart the worker while a leased outbox row exists; after lease expiry another worker safely
  resumes it without duplicate terminal delivery.
- Temporarily deny Redis connectivity: readiness and rate limiting fail closed without leaking the
  endpoint; restore connectivity and verify recovery.

## Worker acceptance, egress and capacity

Use a real staging outbox job and designated mailbox to prove delivery, single-use verification,
retry/idempotency, transactional consistency and recovery after both a systemd restart and VM
restart. Review logs/evidence for secret leakage and confirm in GCP resource inventory that no paid
resource was accidentally created.

Install `vnstat` and measure a continuous 24-hour worker acceptance window. Runtime TX must be
`<= 25 MiB/day`, which projects to approximately `<= 750 MiB/month`. Inspect Google Billing Reports
for unexpected charges/resources as a separate gate. If TX exceeds `25 MiB/day`, stop the worker or
VM, investigate the cause and audit Oracle Cloud Free Tier if necessary. Do not add paid networking
or other resources automatically.

The current planning assumption is approximately 150 registered users per semester. Judge capacity
from measured workload rather than account count alone:

- Worker: outbound traffic, RAM/CPU and restart stability.
- Resend Free: quota and bursts at semester start and during verification, invitation and acceptance
  periods. Report quota pressure as a blocker/capacity risk; do not auto-upgrade.
- Supabase: database size, Storage, egress, avatar usage and chat growth. Do not migrate away while
  quotas remain sufficient.

Preserve avatar crop/resize/compression where supported, avoid unnecessary full-resolution images
in recommendation lists, and prefer thumbnails/optimized delivery when available. This runbook does
not authorize implementing avatar optimization.

OPS-002 is complete only when the disposable restore and migration gates pass; GCP prerequisites,
Supabase direct IPv6/TLS and Resend IPv6/TLS pass; the worker runs a reviewed commit; a real email job
is delivered; retry/idempotency, restart recovery and outbox consistency pass; secrets remain safe;
no paid GCP resource was accidentally created; the 24-hour TX threshold passes; Billing Reports show
no unexpected paid resource; and sanitized evidence is recorded. Until the 24-hour gate passes,
record the task as **BLOCKED / IN ACCEPTANCE**, even when the process starts. Local Docker or mocked
tests cannot substitute for this deployed gate.
