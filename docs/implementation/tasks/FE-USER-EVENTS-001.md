# FE-USER-EVENTS-001 — User Dashboard Event experience

**Status:** DONE — PUSHED / CI PASS / PRODUCTION VERIFIED
**Priority:** P1
**Track:** events
**Assigned:** 2026-10-16
**Dependencies:** `EVENT-OPTIONAL-PUBLISH-001`, `FE-EVENT-DETAIL-TEMPLATE-001`

## Objective

Keep the User Events tab synchronized with every Event displayed by the Landing slider, preserve
registration-optional cards and the canonical Event Detail route, and retain entry-aware back
navigation without creating a second discovery source.

## Scope and implementation

- The real `/user/events` page now uses `useEventSliders` and `selectLandingEventSliders`, the same
  API query/cache and first-five selection used by Landing. Publication, visibility, ready-cover,
  schedule eligibility and backend ordering remain authoritative in the existing Slider service.
- Extended the existing public Slider projection with the Event's persisted `registration_url` and
  `registration_enabled` fields. The frontend parser trims optional URLs, treats missing/null/empty/
  whitespace values as unavailable and continues to require HTTPS when a URL exists. No migration
  or database-model change was introduced.
- Dashboard cards retain Slider image, title, description, date/time when present, location when
  present and canonical order. An enabled usable URL shows Register plus View Details; otherwise the
  Event remains visible and View Details is the only primary action.
- Removed the Event query and registration-card section from `/user/dashboard`; its existing
  Explore Events shortcut remains the single overview entry point.
- Changed View Details to the canonical `/events/:eventId` page with the durable
  `from=user-dashboard` query marker. The shared detail page accepts exactly one recognized marker,
  shows `Back to Event Dashboard`, and returns to `/user/events`. Missing, duplicate or unknown
  context defaults to the existing `Back to home` behavior, including direct access and refresh.
- Removed the nested `/user/events/:eventId` detail route so Event details no longer render inside
  the User layout. Stale nested detail URLs render the embedded not-found boundary.
- Removed the exact `These pages are not available yet.` / German equivalent message, its unused
  localization keys and its placeholder-only accessibility wrapper. Per-item unavailable semantics
  remain available for future placeholder routes.
- Updated English/German loading/error/empty copy while preserving accessible registration/detail
  labels, authentication, feature flags, responsive actions and query refresh behavior.

## Acceptance evidence

- Slider/Dashboard focused frontend validation: 5 files / 43 tests PASS. This covers exact
  first-five membership/order, registration available/unavailable, missing facts, loading, retry,
  locale refresh, 390 px action sizing and cached refetch behavior.
- Feature-enabled Event detail and round-trip validation: 2 files / 21 tests PASS, including User
  Events -> shared detail -> User Events and Landing/direct default-to-home behavior.
- Full frontend: 86 files / 818 tests PASS.
- TypeScript, ESLint and Prettier: PASS.
- Normal and Admin-ON/Public-ON production builds: PASS; only the existing large-chunk advisory
  remains.
- Focused backend Slider tests: 8 PASS on the repository-supported Python 3.12 runtime in a
  disposable local container.
- Backend Ruff, strict mypy and direct Pydantic slider-response contract smoke: PASS.
- Commit `66f44d1a29e18bf6c1a8f64fb39e16002ba58a6c` reached `origin/main`; GitHub Actions run
  `38881976983` passed Frontend and Backend.
- Automatic Vercel Production deployment `7115826436` succeeded for the exact feature SHA. The
  generated deployment URL is
  `https://buddy-web-ver2-hzuq40wmq-dat1507s-projects.vercel.app`; the canonical alias returns 200
  and serves bundle `index-BVBP8HUi.js`.
- Read-only Production API and authenticated browser smoke confirmed the same three Event IDs and
  order on Landing and User Events. Experience Day and Buddy Recruitment have no usable
  registration URL and show View Details only; Kawazo retains Register and View Details.
- Landing detail shows the existing Home return and navigates home. Dashboard-origin detail shows
  exact `Back to Event Dashboard` and returns to `/user/events`. Browser console inspection found
  zero warnings/errors; API live/readiness returned healthy with database/Redis `ok`.
- No database, Event, registration, user, Storage, DNS or provider-configuration mutation occurred.

## Release boundary

The implementation is pushed and Production verified from exact feature commit `66f44d1`. The
read-only acceptance did not submit forms or change Production data. The generated Vercel URL is
deployment-protected and redirects unauthenticated requests to Vercel login; the canonical public
alias was the verified browser and HTTP surface. Render deployment identity/source SHA was not
independently exposed, although the new additive registration fields are directly visible in the
live public Slider API.
