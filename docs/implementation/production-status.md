# Production status

**Last direct read-only verification:** 2026-10-08 10:27 Asia/Saigon
**Owner functional acceptance:** PASS on 2026-10-08
**Mutation performed:** none

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

## Not yet evidenced as complete

- Session recovery, Secure HttpOnly host-only cookie inspection, CSRF negative behavior and private
  cache removal after logout/account change.
- Protocol-level authenticated WebSocket Origin/auth/reconnect and REST history recovery on the
  first-party topology.
- Non-destructive Semester guard/status evidence and the final release secret/history, credential,
  private-backup-access and destructive-control review.
- Production hold-period health/error/job/WSS telemetry, retained Render/Vercel rollback points and
  named rollback/recovery owners sufficient to close `PROD-001`.

Do not upgrade these items to PASS without dated evidence. Do not create test users, send email,
login, change DNS or modify provider configuration during a documentation-only task.

## Verification method

The direct checks used DNS queries and HTTPS GET/OPTIONS requests only. Response bodies recorded here
are deliberately sanitized health/auth boundary outputs; no credential, cookie, Redis value, private
database value or provider secret was read or stored.
