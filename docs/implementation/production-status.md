# Production status

**Last direct verification:** 2026-10-09 11:15 Asia/Saigon
**Owner functional acceptance:** PASS on 2026-10-08
**Mutation boundary:** owner-authorized `origin/main` push and linked Vercel Production deployment of
the Phase 2 frontend and later Landing slideshow corrective release. No backend/database/DNS
configuration, reset, restore, backup retry, secret, account or test-message mutation occurred
during this release verification.

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

## Phase 2 frontend release — 2026-10-09

| Check | Result |
| --- | --- |
| Released Git commit | `2f6f8c8cb4bd15fb4ece1821e8cfc1b4ac3ea8f7` on `origin/main` |
| GitHub/Vercel deployment | Production deployment `6951736865` completed successfully |
| Vercel deployment URL | `https://buddy-web-ver2-9fam0ya8l-dat1507s-projects.vercel.app` |
| Repository checks | Frontend PASS; Backend PASS |
| `GET https://www.vgubuddyprogram.com/` | 200; bundle `index-Deo6vyVU.js` |
| Bundle markers | All five Landing backgrounds, EN/DE Home University copy and first-party API target present |
| Landing desktop visual | PASS at 1536x831; contrast/layout/images/navigation correct; no overflow or Welcome card |
| Landing mobile visual | PASS at 390x844; mobile navigation active, images decoded and no horizontal overflow |
| Landing transition | PASS; 7.1-second sample observed current/next opacity ~0.934/0.066 |
| Browser console | 0 errors; 0 warnings in direct Brave verification |
| API live/readiness | 200 / 200; database/Redis `ok`, email/Storage `configured` |
| Anonymous `/api/auth/me` | 401, `Cache-Control: no-store`, exact first-party allow-origin |
| Authenticated Home University visual | OPEN; no account was used or mutated |

This direct evidence closes `FE-LANDING-BG-001`. It proves deployment of the Home University bundle
but does not close `FE-PROFILE-HOME-UNI-001` until authenticated display/edit/save/reload is visually
accepted. No Vercel runtime-log scan was available through the local environment; the deployed app
is static, direct browser console inspection was clean, and public API health checks passed.

## Landing slideshow corrective release — 2026-10-09

| Check | Result |
| --- | --- |
| Released source commit | `c2fbaf1f1082c6bb5d790d32add3b603f3b251fe` on `origin/main` |
| GitHub/Vercel deployment | Production deployment `6952736000` completed successfully |
| Vercel deployment URL | `https://buddy-web-ver2-pbkwfghyt-dat1507s-projects.vercel.app` |
| Repository checks | Frontend SUCCESS; Backend SUCCESS |
| Public alias / bundle | `https://www.vgubuddyprogram.com/#home`; `index-CC-xLBAH.js` |
| Released slideshow | two stable paint-contained layers; opacity-only compositor path present |
| Desktop three-loop audit | 15 transitions / 2,883 samples; correct order including three 5 -> 1 wraps |
| Blank / undecoded-visible / visible-source-change samples | 0 / 0 / 0 |
| Minimum combined opacity / slideshow layout delta | 1.0000 / 0 px |
| Mobile 390x844 | one live transition PASS; 0 horizontal overflow |
| Normal / reduced-motion reload | two decoded starting layers / one decoded static first image; PASS |
| Browser console | 0 errors; 0 warnings |

This direct evidence closes `FE-LANDING-BG-002` as **DONE / PRODUCTION VERIFIED**. It does not alter
the authenticated Profile acceptance gate or any Phase 1 operational blocker. No Vercel runtime-log
scan was available locally; the static deployed surface, repository checks and direct browser
console were clean.

## Owner Phase 2 acceptance update — 2026-10-09

- The owner directly confirmed that the Production slideshow now changes images smoothly and
  accepted the frontend result. This is consistent with the retained direct Production evidence for
  `FE-LANDING-BG-001` and `FE-LANDING-BG-002`; both remain DONE / PRODUCTION VERIFIED.
- The owner directly confirmed that Home University appears correctly in the Production Profile UI.
  This closes the authenticated display gate only. The original edit/save/reload, empty-clear,
  200-character rejection and unrelated-field stability acceptance has not been directly observed,
  so `FE-PROFILE-HOME-UNI-001` remains open.
- No dynamic Event code from the current local worktree is deployed. The Production Event launch
  flag remains off, and no database, Storage, provider or account mutation is claimed here.

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
