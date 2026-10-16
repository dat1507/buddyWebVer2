# FE-USER-EVENTS-001 — User Dashboard Event experience

**Status:** DONE — COMMITTED LOCALLY / NOT PUSHED
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
- No database, Event, registration, user, Storage, Production configuration or deployment mutation
  occurred. The task was committed locally only; no push or deployment occurred.

## Release boundary

The implementation is committed locally on `main` after base commit `78ddc0f`. Production behavior
has not changed and no live browser or provider claim is made by this task. Push and deployment
remain separate requests.
