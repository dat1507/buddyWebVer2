# ACCEPT-EVENT-001

**Control-plane status:** DONE — FLAG-OFF PRODUCTION SMOKE PASS
**Track:** release-operations
**Priority:** -
**Dependencies (latest extracted):** `EVS-007`, deployed matching frontend/API SHA, migration/head verification,

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Owner execution override — 2026-10-09

Cloud Staging is no longer a prerequisite for the current Event release. Upstash Free provides one
database and the owner reserves it for Production, so restoring a second cloud stack would add cost
or risk Production isolation. The approved sequence is now:

`isolated local acceptance -> Production preflight/rollback -> controlled deployment with flag OFF
-> safe Production smoke -> separate Event launch approval`

The environment changes; the acceptance standard does not. Local PostgreSQL, Redis and object
Storage must be proven separate from Production before any write. Scenarios A–E retain their RBAC,
CSRF, IDOR, versioning, validation, file-security, freshness, responsive and EN/DE requirements.
Production write tests, canonical Event seeding/publishing and changing
`VITE_EVENTS_LAUNCH_ENABLED` remain unauthorized without separate owner approval.

The earlier Staging readiness evidence below remains historical and must not be upgraded to PASS.
Local PASS, Production Smoke PASS and NOT RUN scenarios must be reported separately.

## Isolated local acceptance — PASS 2026-10-10

The owner-approved local replacement gate completed without using Production dependencies:

- dedicated PostgreSQL acceptance database, separate local Redis namespace, local Supabase Storage
  and trusted loopback HTTPS were verified; the email worker stayed off;
- the API harness completed 79 assertions across Admin create/edit/lifecycle, cover replacement,
  public EN/DE projections, signed covers, ordering, RBAC, CSRF, IDOR, optimistic versions,
  allowlists and file validation;
- browser acceptance passed Admin edit, signed cover, slider error/retry, click and deep-link detail,
  EN/DE, desktop/mobile and the post-unpublish empty state with zero runtime/console errors;
- synthetic Events finished non-public, and no Production Event, account, Storage or provider state
  was read for local acceptance or changed;
- Quality Gate E passed 121 focused Event tests, 1,408 backend tests with 37 explicit live skips,
  and 84 files / 774 frontend tests, plus lint/type/build/package/schema/dependency gates.

Detailed sanitized evidence is in
[`accept-event-001-local-acceptance-2026-10-10.md`](../../operations/accept-event-001-local-acceptance-2026-10-10.md).
The active gate is read-only Production baseline/compatibility and executable Vercel/Render
rollback. No push or deployment may occur if rollback remains incomplete. Production Event writes,
data preparation and flag activation remain unauthorized.

## Production code rollout — PASS 2026-10-10

Production preflight directly verified the current Vercel/Render baselines, Alembic head `0021`,
private `event-media` bucket, Event tables, flag-OFF bundle, skew compatibility and executable
rollback. `origin/main` reached `e2ef4c0`; GitHub CI Backend/Frontend succeeded, Vercel deployment
`dpl_Evhx9hudQSBf99P9fxznxtGNg2GS` became READY and Render deployment
`dep-db4v9lqvcj2c73e5jvlg` became LIVE at that application SHA.

Read-only Production smoke passed live/readiness, anonymous auth boundary, canonical empty Event
list/slider, nonexistent detail, anonymous Admin denial, the unchanged static five-poster carousel,
desktop/mobile layout, and existing USER Profile/Matching reads with zero browser warning/error.
Admin Event UI and Event Detail UI are intentionally **NOT RUN** because the Production flag remains
OFF and canonical Event total is zero. No Production Event/account/Storage/database write, seed,
publish, flag, secret or provider-setting change occurred.

Detailed evidence is in
[`accept-event-001-production-release-2026-10-10.md`](../../operations/accept-event-001-production-release-2026-10-10.md).
This task is complete at the approved flag-OFF boundary. Canonical Production data preparation and
enabling `VITE_EVENTS_LAUNCH_ENABLED` require a separate explicit owner approval.

## Staging readiness evidence — 2026-10-09

- `EVS-007` is DONE locally, but no matching frontend/backend Event SHA is deployed to Staging.
- `https://staging.vgubuddyprogram.com` returns 200 but serves the older static Event bundle. The
  bundle does not contain the Admin Event route, so it is not the acceptance candidate.
- Staging API live, readiness and public Event-slider probes return 503 from the suspended provider
  service. The formerly shared Upstash allocation was moved to Production; Staging must not reuse
  Production Redis.
- This checkout has no Vercel/Render/Supabase project linkage or provider credentials available.
  Restoring providers, Redis, database/Storage readiness or accounts was not authorized and was not
  attempted.
- Scenarios A–E are therefore **NOT RUN**, not application FAIL: Admin create/edit/publish, cover
  upload, Landing/detail EN/DE, propagation and RBAC/security require the isolated deployed stack,
  private `event-media` readiness and designated Staging accounts.

This former unblock condition is superseded by the owner execution override above. It records why
cloud Staging was not used; it is not a current request to restore Staging.

## Preserved contract sections

### Legacy lines 8847-8875

#### ACCEPT-EVENT-001 — Real Admin and public staging acceptance

- **Task ID / Status:** `ACCEPT-EVENT-001` — **DEFERRED / POST-DEPLOYMENT**, new; P0 release gate.
- **Objective:** prove the exact product-owner flow on the deployed staging stack before production
  Event opt-in.
- **Dependencies:** `EVS-007`, deployed matching frontend/API SHA, migration/head verification,
  private `event-media` readiness, current ADMIN account.
- **Scope:** one designated disposable Event; Admin create/update/poster/publish; anonymous Landing;
  direct detail; update propagation; USER authorization denial; sanitized evidence and cleanup plan.
- **Non-goals:** production deploy, load test, registration, recap, calendar, ordering/windows or
  destructive database reset.
- **Backend changes:** none; a discovered defect returns to its owning task.
- **Frontend changes:** none; a discovered defect returns to its owning task.
- **Database changes:** verify `alembic current`/expected head only; no manual SQL or migration here.
- **Storage changes:** verify configured private bucket and exercise upload/replacement only through
  Admin UI/API; no Dashboard-direct object manipulation.
- **Security requirements:** use separate ADMIN and normal USER/anonymous sessions; redact email,
  cookies, tokens, signed URLs, object keys and credentials from evidence.
- **Acceptance Criteria / DoD:** Scenario A Admin creates/opens Event, uploads/changes poster, sets
  name/description/date-time/location and saves successfully; Scenario B anonymous/user Landing shows
  it with correct poster; Scenario C click and direct refresh show correct detail; Scenario D Admin
  edit/poster replacement propagates after refetch/F5 and within 60 seconds; Scenario E USER Admin UI
  is denied and direct Admin API mutation returns 403. No unrelated Buddy regression is observed.
- **Tests/Gates:** record deployed SHAs, timestamp, environment, PASS/FAIL per A–E, browser console/
  network sanity, 401/403/CSRF evidence and cleanup outcome without sensitive payloads.
- **Staging acceptance:** this task is the acceptance. Only a complete signed PASS authorizes enabling
  the production Event launch flag; failure keeps the release guard off.
- **Next Task:** explicit product/release approval; no automatic production deployment.


## Cross-reference occurrences outside extracted headings

- Legacy line 8265: - **Launch-scope integrity:** existing non-V2 P0 features must pass their own acceptance gates before production navigation advertises them. The Event/Event Slider/Admin Event track is restored to planned launch scope by controlling Part 27 and must pass \`ACCEPT-EVENT-001\`; until then its existing production feature gate remains off and placeholder routes are not advertised as delivered features.
- Legacy line 8338:   \`ACCEPT-EVENT-001\` passes. After that acceptance, production enables the Event track; the flag is
- Legacy line 8534:   -> ACCEPT-EVENT-001
- Legacy line 8621:   sensitive content during \`ACCEPT-EVENT-001\`.
- Legacy line 8844: - **Staging acceptance:** none; successful automation makes \`ACCEPT-EVENT-001\` ready.
- Legacy line 8845: - **Next Task:** \`ACCEPT-EVENT-001\`.
- Legacy line 8956: 13. \`ACCEPT-EVENT-001\` — Real Admin and public staging acceptance
- Legacy line 8971:   \`ACCEPT-EVENT-001\` with implementation/deployment fixes. A failing acceptance returns to the owner
- Legacy line 8980:   + public/USER flow is exclusively \`ACCEPT-EVENT-001\`.
- Legacy line 9095:    \`ADMIN-009 → FE-031 → FE-014B → EVS-007 → ACCEPT-EVENT-001\`.
