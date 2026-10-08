# Production status

**Last direct verification:** 2026-10-08 15:01 Asia/Saigon
**Owner functional acceptance:** PASS on 2026-10-08
**Mutation boundary:** no source, provider configuration, reset, restore, backup retry or test-message
mutation. Normal USER/ADMIN login/logout occurred; opening the existing conversation may have
reconciled its idempotent read marker.

## Directly observed

| Check | Result |
| --- | --- |
| `api.vgubuddyprogram.com` DNS | CNAME `vgu-buddy-api-production.onrender.com` |
| `www.vgubuddyprogram.com` DNS | CNAME `3d95265b44dec908.vercel-dns-017.com` |
| `GET https://api.vgubuddyprogram.com/api/health/live` | 200, `{"status":"alive"}` |
| `GET https://api.vgubuddyprogram.com/api/health/ready` | 200; database/Redis `ok`, email/Storage `configured` |
| `GET https://www.vgubuddyprogram.com/` | 200 from Vercel |
| Deployed JS API target | Contains `https://api.vgubuddyprogram.com/api` |
| Static Event deployment | Bundle `index-DIl7WhwA.js` contains the five titles from commit `81979ce` |
| Anonymous `GET /api/auth/me` | 401, `Cache-Control: no-store` |
| Login preflight from `https://www.vgubuddyprogram.com` | 200, exact allow-origin and credentials enabled |
| Login preflight from `https://example.invalid` | 400, no allow-origin |

This proves that the first-party DNS cutover is active and the public dependency gate is healthy at
the observation time. It supersedes earlier statements that DNS was still pending.

## Documented operator evidence retained

- Upstash was reallocated to Production, emptied/checked without destructive flush, credentials
  rotated, and staging suspended.
- Supabase Production was migrated zero-to-head and the least-privilege runtime login was verified.
- The Production email Edge worker, secrets, Vault entries and one active Cron were configured; a
  fresh verification message was delivered and consumed through the normal product flow.
- One Production Admin account was provisioned through the repository CLI with no secret committed.
- Restore-blocked-after-new-USER completed atomically and is CLOSED.

See `../operations/production-mvp-readiness-2026-10-07.md` and the dated reconciliation record for
the redacted detail. These are accepted historical observations, not permission to repeat mutations.

## Owner-confirmed functional evidence

The owner explicitly reported successful first-party Production use with no functional errors for
Admin login/Dashboard, User login/Dashboard, Buddy Recommendation, Invitations, Accept Invitation,
Buddy Matching, Chat and related features. Treat these paths as PASS on 2026-10-08 and do not ask
the owner to rerun them solely for another evidence record.

This confirms functional behavior but does not identify cookie attributes, exercise the CSRF
negative path, distinguish WSS from fallback transport, prove protocol-level reconnect/Origin
handling or establish hold/rollback readiness.

## Technical evidence closure — 2026-10-08

The authenticated technical pass established:

- all access, refresh and CSRF cookies were API-host-only `__Host-` cookies with Secure, HttpOnly,
  SameSite=Lax and Path `/`; their observed lifetime classes matched the configured short access
  and long refresh/CSRF design;
- a full page reload restored the USER session and `/api/auth/me` returned 200; logout returned 204
  and removed all three cookie names;
- authenticated notification and conversation WSS handshakes used the exact first-party Origin and
  returned 101; reload re-established both sockets and REST history returned 200;
- authenticated ADMIN GET `/api/admin/semesters/management` returned 200 and the UI enforced the
  `NEW_COHORT` restore block without any destructive action;
- 60 focused web tests and 143 focused API tests passed; the final high-confidence tracked-content
  and Git-history secret scan found no live-secret pattern.

Full redacted evidence and gate reconciliation are in
[`prod-001-technical-evidence-2026-10-08.md`](../operations/prod-001-technical-evidence-2026-10-08.md).

## Current release blockers

- Production Semester status reports `RESET_PREPARATION_FAILED`; the associated private backup is
  `FAILED`, unverified and has no expiry. Render retained two earlier Prepare requests returning
  503. Diagnosing/repairing and safely re-verifying this path requires separate authorization.
- Vercel retains prior Ready frontend deployments, but the Production Render service reports only
  one deploy; no prior backend revision is selectable.
- Named rollback decision/Vercel/Render/database-recovery owners and an accepted post-repair hold
  duration are not recorded.
- The complete encrypted off-site snapshot and disposable DR rehearsal remain post-deploy
  hardening and are not falsely credited as complete recovery evidence.

Do not upgrade these items to PASS without dated evidence. Do not create test users, send email,
retry Semester Prepare, change DNS or modify provider configuration during a documentation-only
task.

## Verification method

The initial direct checks used DNS and HTTPS GET/OPTIONS. The technical pass used owner-entered
credentials in the browser, metadata-only cookie inspection, ordinary session reload/logout,
authenticated WSS handshakes, REST history and the read-only Semester status endpoint. No credential,
cookie value, token, message body, email, private object identity, Redis value, private database row
or provider secret was recorded.
