# Production status

## 2026-10-31 — Dated read-only pre-release provider verification

Vercel buddy-web-ver2 remains ProductionREADY e1a2cc59/main, apps/web/Vite/Node24/default commands;
Previewall-unassigned branches and30-day retention. Both Production Event flags alreadytrue and
exact https://api.vgubuddyprogram.com/api verified after owner step-up. staging domain is a Production
alias, not isolated testing. RenderLive642fc11/main, apps/api, overrides empty, AutoDeployOff/PR
PreviewsOff. API tree equals candidate/main. No provider/config/deploy/rollback/Production data change;
no new Production runtime or authenticated acceptance claimed. UI-only release NO-GO; read current
pre-release report. Older dated records below remain historical.

**Last direct verification:** 2026-10-17 01:30 Asia/Saigon
**Owner functional acceptance:** PASS on 2026-10-08
**Mutation boundary:** owner-authorized `origin/main` push and linked Vercel Production deployment of
the Phase 2 frontend and later Landing slideshow corrective release. No backend/database/DNS
configuration, reset, restore, backup retry, secret, account or test-message mutation occurred
during this release verification.

The later `EVENT-AUDIENCE-SLIDER-001` release authorized the exact source push and its automatic
deployment. Its Production verification was read-only: no Event, user, registration setting,
Storage object, database row, DNS record, feature flag or provider configuration was changed.

The later `FE-USER-EVENTS-001` release authorized exact commit `66f44d1` for push and Production
deployment. Its acceptance was read-only and changed no Event, registration setting, user, Storage
object, database row, DNS record, feature flag or provider configuration.

The later `ACCOUNT-DELETE-001` owner operation explicitly authorized deletion of one exact
Production account and its owned Buddy/profile/session data. This did not authorize or cause a
source, schema, migration, provider-configuration, deployment or unrelated-account change.

The later `EMAIL-TEMPLATE-REDESIGN-001` release authorized exact commit `e4624c0` for push and
deployment. Its verification was read-only after the source release: no account, database, schema,
email, DNS, secret or provider-configuration mutation was performed.

## Directly observed

| Check                                                  | Result                                                                    |
| ------------------------------------------------------ | ------------------------------------------------------------------------- |
| `api.vgubuddyprogram.com` DNS                          | CNAME `vgu-buddy-api-production.onrender.com`                             |
| `www.vgubuddyprogram.com` DNS                          | CNAME `3d95265b44dec908.vercel-dns-017.com`                               |
| `GET https://api.vgubuddyprogram.com/api/health/live`  | 200, `{"status":"alive"}`                                                 |
| `GET https://api.vgubuddyprogram.com/api/health/ready` | 200; database/Redis `ok`, email/Storage `configured`                      |
| `GET https://www.vgubuddyprogram.com/`                 | 200 from Vercel                                                           |
| Deployed JS API target                                 | Contains `https://api.vgubuddyprogram.com/api`                            |
| Static Event deployment                                | Bundle `index-DIl7WhwA.js` contains the five titles from commit `81979ce` |
| Anonymous `GET /api/auth/me`                           | 401, `Cache-Control: no-store`                                            |
| Login preflight from `https://www.vgubuddyprogram.com` | 200, exact allow-origin and credentials enabled                           |
| Login preflight from `https://example.invalid`         | 400, no allow-origin                                                      |

This proves that the first-party DNS cutover is active and the public dependency gate is healthy at
the observation time. It supersedes earlier statements that DNS was still pending.

## Transactional email template release — 2026-10-17

| Check | Result |
| --- | --- |
| Released commit | `e4624c0ca9732f08654c10a30db8ec99fc4bff01` on `origin/main` |
| GitHub Actions | Run `38947149530`; Backend and Frontend SUCCESS for the exact SHA |
| Vercel Production | `dpl_7rbMhAeqPRPy5YbQsqhxKuxdtgHU`; Ready; exact source SHA |
| Vercel deployment URL | `https://buddy-web-ver2-2ghlk7xid-dat1507s-projects.vercel.app` |
| Render Production | `dep-db96nsrm8hqs73e4s43g`; Live; exact source SHA; 57.7-second auto-deploy |
| Supabase Edge | `email-worker` exact `core.ts`; update success; deployment count advanced 1 -> 2 |
| Public health | API live `alive`; ready `ready`; database/Redis `ok`; email/Storage `configured`; site 200 |
| Mutation boundary | No migration or account/database/DNS/secret/provider-configuration change; no test email sent |

The Edge deployment used the existing Production project and preserved its secrets, Cron schedule,
JWT setting and provider configuration. The dashboard source matched the pushed file after
line-ending normalization. Automated rendering/contract coverage remains the acceptance evidence;
Gmail/Outlook rendering and a real transactional-email delivery were not run.

Sanitized details are recorded in
[`email-template-redesign-production-2026-10-17.md`](../operations/email-template-redesign-production-2026-10-17.md).

## Account deletion acceptance — 2026-10-17

| Check                   | Result                                                                                                                 |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Authorization           | Explicit owner confirmation after a read-only scope report                                                             |
| Authentication topology | Custom `app_private.users`; no matching `auth.users` row                                                               |
| Preflight               | Exactly one USER/profile/Match/invitation/session/token/image; zero messages, registrations or `RESTRICT` dependencies |
| Database mutation       | Guarded transaction deleted exactly one application user; existing FK cascades used unchanged                          |
| Buddy cleanup           | Target invitation, ACTIVE Match and conversation absent in both participant orientations                               |
| Profile cleanup         | Profile, preferences, photo metadata and private Storage object absent                                                 |
| Session/auth cleanup    | Refresh session and verification token absent; no Auth user existed                                                    |
| Retention               | Two already-sent outbox rows retained; `recipient_user_id` became `NULL` by existing policy                            |
| Unrelated data          | Other Buddy user/profile preserved; no Event or shared resource deleted                                                |
| Re-registration         | No normalized-email application/Auth row remains; email availability check PASS                                        |
| Runtime health          | Readiness `ready`; database/Redis `ok`; email/Storage `configured`                                                     |
| Release boundary        | No source, schema, migration, config, commit, push or deployment change                                                |

Sanitized details are recorded in
[`account-delete-001-production-2026-10-17.md`](../operations/account-delete-001-production-2026-10-17.md).

## User Events synchronization release — 2026-10-16

| Check                    | Result                                                                                   |
| ------------------------ | ---------------------------------------------------------------------------------------- |
| Released commit          | `66f44d1a29e18bf6c1a8f64fb39e16002ba58a6c` on `origin/main`                              |
| GitHub Actions           | Run `38881976983`; Backend and Frontend SUCCESS for the exact SHA                        |
| GitHub/Vercel deployment | Production deployment `7115826436`; SUCCESS for the exact SHA                            |
| Vercel deployment URL    | `https://buddy-web-ver2-hzuq40wmq-dat1507s-projects.vercel.app`                          |
| Public alias / bundle    | `www.vgubuddyprogram.com` 200; `index-BVBP8HUi.js`                                       |
| Public Slider API        | 3 Events in order: Experience Day, Kawazo, Buddy Recruitment                             |
| User Events              | Same 3 IDs and order as Slider after a fresh authenticated reload                        |
| Registration actions     | Experience Day and Buddy Recruitment: View Details only; Kawazo: Register + View Details |
| Landing detail return    | Existing Home label/href present; click returned to Landing                              |
| Dashboard detail return  | Exact `Back to Event Dashboard`; click returned to `/user/events`                        |
| API health               | live `alive`; ready `ready`; database/Redis `ok`                                         |
| Browser console          | 0 warnings; 0 errors in Landing/detail and authenticated User Events/detail smoke        |

The generated Vercel deployment URL is protected and redirected an unauthenticated HTTP request to
Vercel login; the canonical public alias is the verified serving surface. Render deployment
identity/source SHA was not independently exposed. The new public Slider registration fields and
their frontend behavior are directly visible, but this record does not infer an unobserved provider
deployment identifier. No Production data or configuration mutation occurred.

## Event Audience removal and Slider release — 2026-10-14

| Check                      | Result                                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------------------- |
| Released commit            | `65364a1180032063296898b2c6d8d2a9f59e1b97` on `origin/main`                                             |
| GitHub Actions             | Run `38586750058`; Backend and Frontend SUCCESS for the exact SHA                                       |
| GitHub/Vercel deployment   | Production deployment `7069199596`; SUCCESS for the exact SHA                                           |
| Vercel deployment URL      | `https://buddy-web-ver2-n5hhkpzst-dat1507s-projects.vercel.app`                                         |
| Public alias / bundle      | `www.vgubuddyprogram.com` 200; `index-DfxH7DYv.js`                                                      |
| Effective feature behavior | Dynamic public EN/DE Slider and Admin Event form both available                                         |
| Public API EN / DE         | Each returned the same two PUBLISHED, cover-ready Events                                                |
| Public Events              | Kawazo `5a3c57aa-b676-4df3-92cd-414c82ea2c13`; Buddy Recruitment `98951257-9edc-4ed2-a64f-f5ea464ef771` |
| Admin contract             | Production OpenAPI draft input and list filter contain no `visibility`                                  |
| Admin UI                   | Create form contains no Audience field; inspected without submitting                                    |
| Slider desktop/mobile      | EN/DE, rapid input and 390 × 844 no-horizontal-overflow checks PASS                                     |
| Browser console            | 0 errors; 0 warnings during bounded smoke                                                               |

The API and live Slider confirm that legacy published `MEMBERS` no longer remains hidden solely by
that stored value. This supersedes the older `ADMIN-010` statement that Buddy Recruitment visibility
required a Production data correction. No broad update or Event mutation was performed.

The release includes reversible migration `0022_public_event_visibility_default`, which changes
only the database server default and performs no data rewrite. Its Production Alembic revision was
not independently queried. The new backend behavior and OpenAPI contract are directly visible, but
the Render deployment identity/source SHA was not exposed through the available read-only access.
Available browser profiles were authenticated, so anonymous frontend rendering was not repeated by
signing out; unauthenticated public API reads returned 200 and matched the rendered two-Event Slider.

## Phase 2 frontend release — 2026-10-09

| Check                                  | Result                                                                                      |
| -------------------------------------- | ------------------------------------------------------------------------------------------- |
| Released Git commit                    | `2f6f8c8cb4bd15fb4ece1821e8cfc1b4ac3ea8f7` on `origin/main`                                 |
| GitHub/Vercel deployment               | Production deployment `6951736865` completed successfully                                   |
| Vercel deployment URL                  | `https://buddy-web-ver2-9fam0ya8l-dat1507s-projects.vercel.app`                             |
| Repository checks                      | Frontend PASS; Backend PASS                                                                 |
| `GET https://www.vgubuddyprogram.com/` | 200; bundle `index-Deo6vyVU.js`                                                             |
| Bundle markers                         | All five Landing backgrounds, EN/DE Home University copy and first-party API target present |
| Landing desktop visual                 | PASS at 1536x831; contrast/layout/images/navigation correct; no overflow or Welcome card    |
| Landing mobile visual                  | PASS at 390x844; mobile navigation active, images decoded and no horizontal overflow        |
| Landing transition                     | PASS; 7.1-second sample observed current/next opacity ~0.934/0.066                          |
| Browser console                        | 0 errors; 0 warnings in direct Brave verification                                           |
| API live/readiness                     | 200 / 200; database/Redis `ok`, email/Storage `configured`                                  |
| Anonymous `/api/auth/me`               | 401, `Cache-Control: no-store`, exact first-party allow-origin                              |
| Authenticated Home University visual   | OPEN; no account was used or mutated                                                        |

This direct evidence closes `FE-LANDING-BG-001`. It proves deployment of the Home University bundle
but does not close `FE-PROFILE-HOME-UNI-001` until authenticated display/edit/save/reload is visually
accepted. No Vercel runtime-log scan was available through the local environment; the deployed app
is static, direct browser console inspection was clean, and public API health checks passed.

## Landing slideshow corrective release — 2026-10-09

| Check                                                     | Result                                                                     |
| --------------------------------------------------------- | -------------------------------------------------------------------------- |
| Released source commit                                    | `c2fbaf1f1082c6bb5d790d32add3b603f3b251fe` on `origin/main`                |
| GitHub/Vercel deployment                                  | Production deployment `6952736000` completed successfully                  |
| Vercel deployment URL                                     | `https://buddy-web-ver2-pbkwfghyt-dat1507s-projects.vercel.app`            |
| Repository checks                                         | Frontend SUCCESS; Backend SUCCESS                                          |
| Public alias / bundle                                     | `https://www.vgubuddyprogram.com/#home`; `index-CC-xLBAH.js`               |
| Released slideshow                                        | two stable paint-contained layers; opacity-only compositor path present    |
| Desktop three-loop audit                                  | 15 transitions / 2,883 samples; correct order including three 5 -> 1 wraps |
| Blank / undecoded-visible / visible-source-change samples | 0 / 0 / 0                                                                  |
| Minimum combined opacity / slideshow layout delta         | 1.0000 / 0 px                                                              |
| Mobile 390x844                                            | one live transition PASS; 0 horizontal overflow                            |
| Normal / reduced-motion reload                            | two decoded starting layers / one decoded static first image; PASS         |
| Browser console                                           | 0 errors; 0 warnings                                                       |

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
- At this dated frontend-only checkpoint, no dynamic Event code was deployed. The newer flag-OFF
  Event code release below supersedes that deployment statement without enabling Event launch.

## Dynamic Event release readiness — 2026-10-09

Read-only Staging probes and local release verification establish the following current boundary:

| Check                              | Result                                                                                                 |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Local Event regression             | PASS on supported Python 3.12: backend 1,407 PASS / 37 SKIP; Event 111 PASS; frontend 773 PASS         |
| Owner Landing limit                | PASS locally: first five canonical API results only; backend 12-row bound remains transport/query-only |
| Production Event launch flag       | OFF; released static five-poster fallback remains active                                               |
| Staging frontend                   | 200, but older static bundle; matching Admin/Event SHA not deployed                                    |
| Staging API                        | live/readiness/Event-slider probes return 503; provider service is suspended                           |
| Staging isolation                  | No isolated Redis is available after the former allocation moved to Production                         |
| Provider access from this checkout | No Vercel/Render/Supabase linkage or credentials available                                             |
| `ACCEPT-EVENT-001` A–E             | NOT RUN; environment prerequisite blocked                                                              |
| Production mutation                | None; no push, deployment, data write, flag change or provider change                                  |

This Staging-based release conclusion is superseded by the owner execution strategy below. Its
observations remain historical and are not converted to PASS.

### Event execution strategy override — 2026-10-09

The owner chose not to restore cloud Staging because the single Upstash Free database is reserved
for Production and no paid service should be added. The replacement gate is isolated local A–E,
Production baseline plus executable frontend/backend rollback, controlled deployment with the Event
flag OFF, and safe read-only/non-destructive Production smoke. Security and quality criteria remain
unchanged. Production Event writes, canonical data publication and enabling the flag require
separate approval.

### Isolated local Event acceptance — PASS 2026-10-10

The replacement local gate and complete Quality Gate E now pass. A dedicated PostgreSQL acceptance
database, isolated local Redis namespace, local Supabase Storage and trusted loopback HTTPS were
used; no Production dependency, account or Event row participated. The API harness passed 79
assertions and browser acceptance passed Admin edit, signed cover, retry, Event detail/deep-link
EN/DE, desktop/mobile and empty-state behavior with zero runtime/console errors. Current regression
evidence is 121 focused Event PASS, backend 1,408 PASS / 37 explicit live SKIP and frontend 84 files
/ 774 PASS, with lint/type/build/schema/package/dependency gates passing.

This newer evidence supersedes only the historical `NOT RUN` local-acceptance conclusion above; it
does not change that cloud Staging remains unused. At this local-acceptance checkpoint Production
was still unchanged and the Event flag was OFF. Full evidence is in
[`accept-event-001-local-acceptance-2026-10-10.md`](../operations/accept-event-001-local-acceptance-2026-10-10.md).

### Flag-OFF Production code release — PASS 2026-10-10

- `origin/main` reached application SHA `e2ef4c0`; GitHub Actions run `38037425291` completed
  Backend SUCCESS and Frontend SUCCESS.
- Vercel deployment `dpl_Evhx9hudQSBf99P9fxznxtGNg2GS` is READY and Render deployment
  `dep-db4v9lqvcj2c73e5jvlg` is LIVE at the application SHA.
- Direct Supabase read-only evidence confirmed Alembic `0021_restore_runtime_permissions`, the
  `app_private.events`/`event_media` tables and private 5 MiB JPEG/PNG/WebP `event-media` bucket.
- Public smoke returned live/readiness 200, anonymous auth 401/no-store, canonical slider 200 `[]`,
  Event list 200 with total zero, nonexistent Event detail 404/no-store and anonymous Admin Event
  list 401/no-store.
- Production bundle `index-phrHnhsS.js` retains all five static Event titles and contains neither
  canonical slider nor Admin Event API markers. Desktop/mobile Landing and an existing USER
  Profile/Matching read passed with zero browser warning/error.
- Admin Event UI and Event Detail UI remain intentionally NOT RUN: the flag is OFF and canonical
  Event total is zero. No Production Event/account/Storage/database write, seed, publish, flag,
  secret or provider-setting change occurred.

Full evidence is in
[`accept-event-001-production-release-2026-10-10.md`](../operations/accept-event-001-production-release-2026-10-10.md).
`ACCEPT-EVENT-001` is complete at the approved flag-OFF boundary. Event launch remains a separate
owner decision.

### Final deployment verification and launch preparation — 2026-10-10

- Repository HEAD and `origin/main` are `e0ef343`; GitHub Actions run `38038014039` completed
  Backend SUCCESS and Frontend SUCCESS with no failing job.
- Vercel docs-only deployment `dpl_3ndKHjjd57dNtye1X1k3Sw2Pd5HY` is READY. Production still serves
  accepted application bundle `index-phrHnhsS.js`, with all five static titles and no canonical
  Event API markers.
- Render did not deploy the docs-only commit. `dep-db4v9lqvcj2c73e5jvlg` remains LIVE at
  application SHA `e2ef4c0`; prior `d15cb1d` is retained with native Rollback.
- Public site, API live and readiness are 200; database/Redis are `ok`, email/Storage are
  `configured`; the slider remains 200 `[]`.
- A direct read-only database count found zero rows in `app_private.events`, including zero DRAFT,
  PUBLISHED, CANCELLED and cover-linked rows.
- Vercel has no `VITE_EVENTS_LAUNCH_ENABLED` entry. The Production default remains OFF.

The current frontend does not support the preferred Admin-ON/Public-OFF rollout with flags alone.
`VITE_EVENTS_LAUNCH_ENABLED` controls the live Landing slider and most public/User/Admin Event
surfaces together; Admin create/edit child routes are separately registered behind ADMIN RBAC even
when the flag is OFF. A small, separately approved source change must split Admin management from
public-live activation and gate all Admin Event routes consistently. No source, flag or provider
change was made during this verification.

### Static-to-canonical Production data preparation

The current fallback owns five reusable project posters and names, in canonical display order:
Recruitment, Club Fair 26, Experience Day, Christmas and Halloween. No committed source supplies a
trustworthy future date/time, timezone, location or full EN/DE description. Those values must not be
inferred from a poster or title.

After local acceptance, a safe flag-OFF code rollout/smoke, and separate launch approval, an Admin
should create five DRAFT canonical records through the product UI, upload the existing posters,
enter owner-approved EN/DE content and confirm each future schedule/timezone/location. Publish only
records that are genuinely upcoming and have ready covers; verify the API order and the first-five
Landing result before enabling the flag. If no record qualifies, the live section intentionally
becomes empty, so the flag must remain off until the owner accepts the prepared dataset. No
Production seed or data mutation was performed.

### Rollback boundary

Turning the frontend launch flag off and redeploying restores the existing static five-poster
carousel without deleting canonical Event data. Vercel currently marks the accepted `e2ef4c0`
application deployment as a rollback candidate behind the docs-only `e0ef343` deployment. The
pre-Event `253849d` and `c2fbaf1` deployments remain READY immutable deployments but are no longer
reported as native rollback candidates; an operator can explicitly promote the selected READY
Production deployment if an Event-code rollback is required. The live Render `e2ef4c0` deploy
exposes a native rollback action to retained `d15cb1d`; the specific-commit redeploy flow was also
verified without executing it. The Event work adds no migration, so code rollback requires no
database downgrade. Named release/recovery owners remain a separate `PROD-001` requirement, not an
Event-release rollback gap.

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
  `FAILED`, unverified and has no expiry. Render retained two earlier Prepare requests returning 503. Diagnosing/repairing and safely re-verifying this path requires separate authorization.
- Vercel and Render now retain executable frontend/backend code rollback points from the
  2026-10-10 Event rollout. This closes the former missing-Render-deploy blocker only.
- Named rollback decision/Vercel/Render/database-recovery owners and an accepted post-repair hold
  duration are not recorded.
- The complete encrypted off-site snapshot and disposable DR rehearsal remain post-deploy
  hardening and are not falsely credited as complete recovery evidence.

Do not upgrade these items to PASS without dated evidence. Do not create test users, send email,
retry Semester Prepare, change DNS or modify provider configuration during a documentation-only
task.

## EVENT-FLAG-SPLIT Production preflight — 2026-10-11

- The authenticated Vercel dashboard confirms project `buddy-web-ver2` in the expected team and the
  current `e0ef343` Production deployment READY. Earlier accepted application deployments remain
  READY rollback candidates.
- Production environment-variable metadata contains neither `VITE_ADMIN_EVENTS_ENABLED` nor
  `VITE_PUBLIC_EVENTS_ENABLED`; `VITE_EVENTS_LAUNCH_ENABLED` is also absent. No value was revealed or
  changed. The strict frontend resolver therefore compiles both Event surfaces OFF.
- The release is frontend-only. No backend, migration, database, Storage, Redis, DNS, secret or
  account change is required. Render's accepted live `e2ef4c0` deployment and retained `d15cb1d`
  rollback evidence remain the controlling baseline.
- The authorized rollout must preserve the static five-poster Landing, hidden Admin/public Event UI
  and no Landing slider API request. It must stop before Admin-only activation or any Production
  Event write.

### EVENT-FLAG-SPLIT release verification — 2026-10-11

- `b3799669cf5fdb463cf03629e05b4b98fefe1f0a` reached `origin/main`. GitHub Actions run
  `38077938121` completed Backend and Frontend with SUCCESS.
- Vercel deployment `dpl_GGJ7ZaVioxoNt3nLcsMd7XHY8y36` is READY. Production serves
  `index-XtzcBb4D.js`; all five static Event titles are present and the live slider endpoint and
  `/admin/events` markers are absent.
- Landing generated zero Event-slider requests and zero Event links, with no horizontal overflow or
  browser warning/error. Direct public Event detail returned the normal 404 boundary.
- The existing authenticated USER session rendered Profile and Buddy Matching normally, without an
  Event navigation entry. A direct Admin Event URL rendered neither an Admin layout nor Event
  management UI.
- Site, API live and readiness are 200; database/Redis are `ok`, email/Storage are `configured`.
- No backend file changed. GitHub reports only the successful Vercel Production deployment for this
  SHA; Render was not expected to rebuild and the accepted `e2ef4c0` live / `d15cb1d` rollback
  baseline remains controlling. The Render dashboard session was signed out, so no login or provider
  mutation was attempted merely to repeat that deployment-ID observation.
- Both new Vercel keys and the legacy key remain absent. No flag, Event/account data, database,
  Storage, Redis, DNS, secret or provider setting changed.

Status: **DEPLOYED — AWAITING ADMIN ACTIVATION**. Admin-only activation, controlled Production write
acceptance and public-live activation still require separate explicit approvals.

## ADMIN-EVENT-ACTIVATION — 2026-10-11

- Vercel Production now contains the single Config value `VITE_ADMIN_EVENTS_ENABLED=true`.
  `VITE_PUBLIC_EVENTS_ENABLED` and the legacy key remain absent; public live Events therefore remain
  OFF and the legacy key cannot enable either surface.
- A required rebuild created Production deployment `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4`, READY from
  source `b3799669cf5fdb463cf03629e05b4b98fefe1f0a`. The live bundle is
  `index-CrsPaw6k.js` (919,216 bytes): Admin list/create/metrics markers are present, while the live
  slider endpoint and legacy markers are absent.
- The prior `dpl_GGJ7ZaVioxoNt3nLcsMd7XHY8y36` deployment and other READY Production deployments
  remain available rollback points. No backend file changed or Render restart was required; the
  accepted `e2ef4c0` live / `d15cb1d` rollback baseline remains controlling.
- API live/readiness returned 200 with database/Redis `ok` and email/Storage `configured`. Landing
  desktop and 390 x 844 retain all five static posters, have no Event links, slider request or
  horizontal overflow, and recorded zero console warning/error.
- Existing USER Profile and Buddy Matching reads pass. USER direct Admin Event access returns to
  the public surface; Anonymous redirects to Admin Login; the anonymous Admin Event API returns
  401 with no-store.
- After the owner completed ADMIN login, authenticated read-only smoke passed. Dashboard exposes the
  Events navigation item and renders Published/Upcoming Event metrics as `Not available`.
  `/admin/events` loads its filter/table shell and reports `0–0 of 0`; `/admin/events/new` renders
  the localized DRAFT form without submission; a valid-shaped nonexistent edit URL returns
  `Event not found`. No warning/error was recorded on the Admin list, Create or Edit-boundary pages.
  A populated edit form is not applicable while the Production Event inventory is empty.
- No Event/account/database/Storage write, form submission, upload, status transition, delete,
  Supabase/Redis/DNS/secret change or public activation occurred.

This was the accepted pre-write continuation point. A newer owner-approved write acceptance is
recorded below; this paragraph remains the historical activation boundary.

### Production write acceptance — 2026-10-11

- The owner authorized exactly one synthetic DRAFT and the bounded Create -> reload -> cover
  upload/replace -> Edit -> stale-version conflict sequence. No publish, status transition,
  delete/cleanup or public-flag change was authorized.
- `POST /api/admin/events` returned 201 for Event
  `132dfbb1-b966-4cd0-a02e-901cd50cc8f5`; reload GET returned 200 with version 1. The final row is
  version 6, `DRAFT`, `MEMBERS`, registration OFF, `published_at=NULL`, and organizer
  `VGU Buddy QA (synthetic, edited)`.
- Cover A created media `9f00a563-24d7-48d5-87ac-33c77abf5c9c` and private object
  `event-media/0b9f13bd-ab39-4563-b835-eaea8d6067fe.webp`. Cover B replaced it with media
  `e3f58e3f-f1d4-44aa-839c-c7f699602215` and retained private object
  `event-media/b566eab7-7807-4c2b-a99f-dd898e1dfe7d.webp`. Both upload responses reported
  `cleanup_pending=false`; the authorized replacement path automatically removed cover A from
  metadata and Storage. No manual delete or cleanup ran.
- The normal Edit advanced version 5 -> 6. A second tab retained version 5; its save returned 409
  and displayed the reload/review message. Database state stayed at version 6 and no audit row was
  created for the rejected stale request.
- Six expected audit rows exist: one create, three accepted content updates and two media replaces.
  Event-related transactional outbox rows: zero.
- Anonymous public detail EN/DE returns 404. Slider EN/DE returns `[]`. The flag-OFF Landing contains
  no synthetic title, Event ID or link and made zero `/event-sliders` requests. Admin, stale-conflict
  and public Landing tabs recorded zero browser warning/error entries.
- API live/readiness remains 200 with database/Redis `ok` and email/Storage `configured`.
  `VITE_PUBLIC_EVENTS_ENABLED` remains absent/OFF; no source code, deployment, real Event, user data,
  DNS, secret or provider configuration changed.

Detailed sanitized evidence:
[`admin-event-production-write-acceptance-2026-10-11.md`](../operations/admin-event-production-write-acceptance-2026-10-11.md).

Status: **DONE — PRODUCTION WRITE ACCEPTANCE PASS / DRAFT RETAINED**. Publication, status change,
retained-DRAFT cleanup/delete and public-live activation require new explicit approvals.

## Event visibility diagnosis — 2026-10-14

- Authenticated Admin inventory was read only. It contained the retained synthetic DRAFT plus real
  Event `0a9fe1f9-ea26-4426-bfd8-8900113de46f`, titled
  `𝐅𝐈𝐄𝐋𝐃 𝐓𝐑𝐈𝐏 𝐓𝐎 𝐊𝐀𝐖𝐀𝐙𝐎 𝐂𝐑𝐀𝐅𝐓 𝐕𝐈𝐋𝐋𝐀𝐆𝐄`.
- The real Event is `PUBLISHED`, `PUBLIC`, cover-ready and complete in EN/DE, but its 2026-10-10
  schedule is `COMPLETED`. Slider reads in EN/DE return `200 []` because the canonical projection is
  upcoming-only (`start_date >= now()` plus published/public/non-deleted/ready-cover eligibility).
- Anonymous detail reads in EN/DE return 200 with canonical content. This confirms the record,
  publication boundary and detail API are healthy; completed Events remain directly readable.
- Production still serves `index-CrsPaw6k.js`. Admin Events are enabled, while
  `VITE_PUBLIC_EVENTS_ENABLED` remains OFF. The Landing retains five static posters, generates no
  live Event link/request, and a direct Event route remains at the frontend 404 boundary.
- Local `FE-EVENT-DETAIL-TEMPLATE-001` implementation and verification pass, but are not deployed.
  No Production Event/account/database/Storage/flag/configuration/deployment mutation occurred.

Status: **DIAGNOSIS CONFIRMED / LOCAL IMPLEMENTATION PASS / NOT DEPLOYED**. Public release requires
separate approval, a truthful upcoming eligible Event and a rebuilt frontend with the public flag
set to exact `true`; no backend migration or deployment is required.

## Kawazo schedule acceptance and public-release preflight — 2026-10-14

- The owner explicitly authorized only a schedule correction for Kawazo
  (`0a9fe1f9-ea26-4426-bfd8-8900113de46f`). Admin API version 3 was fresh immediately before the
  write. The accepted update set `start_date=2026-11-10T00:20:00Z` and
  `end_date=2026-11-10T12:00:00Z`, preserving 07:20–19:00 Asia/Ho_Chi_Minh and the 11h40m duration.
- Fresh Admin reads showed only the authorized dates plus derived `phase=UPCOMING`, `version=4` and
  `updated_at` changed. Status remains `PUBLISHED`; visibility remains `PUBLIC`; localized content,
  ready cover, timezone, registration URL/state/deadline and `published_at` are unchanged.
- The update endpoint records `event.update` in the same transaction as the business write. The 200
  response proves both committed together. There is no implemented audit-log read API/UI in this
  release, so no independent audit-row retrieval is claimed.
- Anonymous EN/DE detail reads returned 200 with the new schedule and unchanged canonical content.
  The public Slider returned exactly Kawazo with its canonical detail link.
- A final refreshed Admin inventory showed exactly two rows: Kawazo as
  `PUBLISHED`/`PUBLIC`/`UPCOMING`, and retained acceptance Event
  `132dfbb1-b966-4cd0-a02e-901cd50cc8f5` as `DRAFT`/`MEMBERS` with no schedule. The retained DRAFT
  still returns the public 404 boundary and does not appear in the Slider.
- Vercel current Production remains `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4` from `b379966`, with
  `VITE_ADMIN_EVENTS_ENABLED=true` and `VITE_PUBLIC_EVENTS_ENABLED` absent/OFF. Retained READY
  deployment `dpl_GGJ7ZaVioxoNt3nLcsMd7XHY8y36` remains available; no provider config or deployment
  changed.
- Verified local frontend release commit `9df8c64493c3273f32e68f7193fb6b9ad70ec89d` is one commit
  ahead of `origin/main`. It passed 85 files / 791 tests, focused 8 files / 62 tests,
  TypeScript/ESLint/Prettier, public-OFF/public-ON builds and local browser acceptance against
  read-only Production Event APIs. It has not been pushed or deployed.

Detailed sanitized evidence:
[`event-kawazo-production-release-preflight-2026-10-14.md`](../operations/event-kawazo-production-release-preflight-2026-10-14.md).

Status: **READY FOR RELEASE APPROVAL — NOT DEPLOYED**. The only Production data mutation was the
authorized Kawazo schedule update. Public activation, push and deployment still require a new
explicit approval. No backend release or migration is required.

## Event Detail and Slider release attempt — rolled back — 2026-10-14

- Exact frontend commit `9df8c64493c3273f32e68f7193fb6b9ad70ec89d` reached `origin/main`.
  GitHub Actions run `38551287304` passed both required jobs: `CI / Frontend` and `CI / Backend`.
- Automatic Vercel deployment `dpl_ArkWFd8NjyVF4GeiQ1h4ANbMarzu` was the intermediate Public-OFF
  build. After CI, Production Config was set to Public ON while preserving Admin ON, and deployment
  `dpl_7jRJsyD4AqJtFMKMEUHx72Fpba8K` rebuilt the exact SHA and became the serving Production
  artifact.
- Immediate eligibility reads returned exactly Kawazo in both Slider locales. Anonymous/User EN/DE
  Slider and detail, canonical click/direct reload, normal-User/Admin boundaries, desktop/mobile
  layout, unaffected homepage sections and console/network health passed.
- Mandatory content consistency failed: the live poster advertised `EVENT DATE 10/10/2026` and
  `7:40–16:30`, but the canonical Event detail published November 10, 2026 and 07:20–19:00. The
  accepted registration-deadline condition was not investigated and is unrelated to this failure.
- Rollout stopped. Deployment `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4` was promoted and Production now
  serves its `b379966` bundle `index-CrsPaw6k.js`. Direct HTTPS verification returned HTML/bundle
  200, with Admin Event markers present and public Slider/detail-route markers absent. Browser
  verification showed the static five-poster carousel with zero Event links, the public Event 404
  boundary and the two-row Admin inventory with zero warning/error.
- Production Config was restored to `VITE_PUBLIC_EVENTS_ENABLED=false` for future builds;
  `VITE_ADMIN_EVENTS_ENABLED=true` was preserved. No Event, registration setting, cover/Storage
  object, user, backend, schema or DNS data was changed. The independently retrieved Production
  audit row remains unavailable and is not newly claimed.
- Post-recovery API checks returned live 200 and readiness 200/`ready`. EN and DE Slider reads each
  still returned exactly one item containing Kawazo and neither contained the retained synthetic
  DRAFT; the rolled-back frontend does not request or render that projection while Public Events is
  OFF.

Status: **RELEASE ROLLED BACK — CONTENT CORRECTION REQUIRED**. `origin/main` retains the approved
frontend commit, while Production aliases serve the verified rollback artifact. Correcting the
Kawazo content and attempting another public release both require fresh explicit authorization.

## Event Detail and Slider final owner-accepted release — 2026-10-14

- The owner explicitly accepted the Kawazo poster versus canonical schedule discrepancy as an
  out-of-scope content issue and authorized release without modifying the Event, poster or
  registration configuration.
- Exact commit `9df8c64493c3273f32e68f7193fb6b9ad70ec89d` remains on local and remote `main`; no redundant
  source commit or push was created. GitHub Actions run `38551287304` passed Frontend and Backend.
- Vercel Production Config now has `VITE_PUBLIC_EVENTS_ENABLED=true` and
  `VITE_ADMIN_EVENTS_ENABLED=true`. Deployment `dpl_48YExmcZG4YREaUGGUmePsaZ9NP2` is Ready from
  the exact SHA and owns `www.vgubuddyprogram.com`.
- The live HTML and `index-kimW3TwX.js` return 200. The bundle contains public Slider and Admin Event
  markers and no longer contains the old static `Recruitment` or `Club Fair 26` Event titles.
- No-cookie EN/DE Slider reads each returned exactly Kawazo. Its canonical detail returned 200; the
  retained synthetic DRAFT was absent from both Sliders and its public detail returned 404.
- Browser smoke passed for dynamic EN/DE Slider and detail, card navigation, direct refresh,
  normal-User denial of Admin Events, authenticated Admin two-row inventory, desktop and 390 x 844
  layouts, console/network health and unrelated Landing sections.
- Fresh `/api/health/live` and `/api/health/ready` reads returned 200; readiness was `ready` with
  database/Redis `ok` and email/Storage `configured`.
- Retained deployment `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4` remains the intended Admin-ON/public-OFF
  rollback baseline. No Event, registration setting, cover/Storage object, user, backend, schema or
  DNS state changed in this final release.

Status: **PASS — COMMITTED, DEPLOYED, AND PRODUCTION-VERIFIED**. The accepted poster discrepancy is
recorded but is not a release failure. The specific Production audit row was not independently
retrieved; only the reviewed transactional implementation and existing rollback-on-audit-failure
tests support that evidence.

## Optional Event publication implementation push — 2026-10-14

- Commit `1f94629d8dd68e92966d61eb14b9a817c1fb991e`, directly based on
  `9df8c64493c3273f32e68f7193fb6b9ad70ec89d`, reached `origin/main`.
- The commit contains the 23 intended implementation, focused-test, localization and task-record
  files for `EVENT-OPTIONAL-PUBLISH-001`; pre-existing dirty documentation and local Supabase
  metadata were not staged or included.
- GitHub Actions run `38571496427` passed both Frontend and Backend for the exact commit.
- No deployment, feature-flag change, migration or Production data/configuration write occurred.

Status: **PASS — COMMITTED / CI PASS / NOT DEPLOYED**. Deployment remains separately gated.

## Event visibility and Admin deletion implementation push — 2026-10-14

- Commit `ed250f52920b8bf415ea87224462cd10aa923df9`, directly based on
  `1f94629d8dd68e92966d61eb14b9a817c1fb991e`, reached `origin/main`.
- GitHub Actions run `38576202814` passed Frontend and Backend for the exact commit.
- Production anonymous EN/DE Event list and Slider reads returned only Field trip. Its public
  projection confirms `PUBLISHED`/`PUBLIC`, future schedule and a ready cover. A verified USER read
  returned Buddy Recruitment `b62cee68-8f9a-4206-89b7-d84b74fd4e8b` in both locales as
  `PUBLISHED`/`MEMBERS`, unscheduled, location-free, registration OFF and cover-ready, directly
  confirming the anonymous eligibility failure.
- Source evidence found that the Admin form had hidden Audience while defaulting new drafts to
  `MEMBERS`. The pushed correction defaults new drafts to `PUBLIC`, restores explicit Audience
  editing and adds the dependency-aware confirmed Delete action to Admin Inventory.
- Push-triggered GitHub Deployment `7067400901` completed successfully in Vercel Production for the
  exact SHA. `www` serves `index-Bkc4hubM.js`, which contains the new deletion contract and UI.
- No backend deployment, feature-flag change, Event mutation, delete, media/Storage write, migration
  or Production configuration change occurred.

Status: **FRONTEND AUTO-DEPLOYED / BACKEND & DATA PENDING**. Backend release and Buddy Recruitment
visibility correction remain separately gated.

## Verification method

The initial direct checks used DNS and HTTPS GET/OPTIONS. The technical pass used owner-entered
credentials in the browser, metadata-only cookie inspection, ordinary session reload/logout,
authenticated WSS handshakes, REST history and the read-only Semester status endpoint. No credential,
cookie value, token, message body, email, private object identity, Redis value, private database row
or provider secret was recorded.
