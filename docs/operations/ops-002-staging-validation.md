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
- Worker: a separately running instance of `python -m app.cli email-worker`; it must not run inside
  the request process.
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
used to impersonate the required worker. Render Background Workers have no Free compute plan; the
minimum `0.5c-512mb` worker is a paid resource and must not be created without explicit cost
approval.

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

OPS-002 is complete only when every item above has recorded staging evidence and the restored backup
has been verified. Local Docker or mocked tests cannot substitute for this deployed gate.
