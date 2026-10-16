# EVENT-AUDIENCE-SLIDER-001 — Remove Event Audience and smooth the Landing Event Slider

**Status:** DONE — PUSHED / CI PASS / PRODUCTION VERIFIED  
**Completed:** 2026-10-14 (Asia/Saigon)  
**Release commit:** `65364a1180032063296898b2c6d8d2a9f59e1b97`  
**Direct parent:** `ed250f52920b8bf415ea87224462cd10aa923df9`

## Scope and outcome

The obsolete Event Audience choice is removed from Admin create/edit/inventory UI, frontend form
state and write contracts. The backend defaults drafts to `PUBLIC`, normalizes publish to `PUBLIC`,
and public list/detail/media eligibility now depends on publication/deletion/cover readiness rather
than the legacy visibility value. The legacy database column and enum remain temporarily for
rollback compatibility; API responses accept the deprecated field only at the rolling-deploy wire
boundary and remove it from the frontend Event model.

Existing `PUBLISHED` rows that still store `MEMBERS` therefore become publicly eligible without a
Production data rewrite. Draft, deleted, unpublished, non-ready-cover and Admin authorization
boundaries remain enforced. Registration fields and HTTPS validation are unchanged.

A reversible, data-free migration `0022_public_event_visibility_default` changes the database
column default from `MEMBERS` to `PUBLIC`; downgrade restores the old default. It contains no
`UPDATE` and was not manually applied to Production during this task. Production migration-head
application was not independently retrieved, so no claim is made that the Production schema
default has advanced. Runtime behavior does not depend on rewriting existing rows.

The Slider stutter was traced to bubbled child transition events clearing the track transition,
controls being disabled during movement, adjacent image lazy loading, and manual/auto navigation
state competing at boundaries. The fix guards the track's `transform` transition completion,
queues rapid directions, keeps controls operable, uses `translate3d`, eagerly decodes adjacent
covers, preserves stable geometry, supports horizontal touch swipes with vertical page scrolling,
and keeps reduced-motion behavior.

## Verification

- Focused backend: 77 passed.
- Focused frontend: 4 files / 32 passed.
- Full backend: 1,415 passed, 37 explicit live skips.
- Full frontend: 86 files / 806 tests passed.
- Ruff, mypy (292 source files), TypeScript, ESLint, Prettier and `git diff --check`: PASS.
- Alembic: one head, `0022_public_event_visibility_default`; offline upgrade/downgrade and no-data-
  rewrite assertions pass.
- Production build with `VITE_ADMIN_EVENTS_ENABLED=true` and
  `VITE_PUBLIC_EVENTS_ENABLED=true`: PASS; existing large-chunk warning only.
- Local browser: desktop EN/DE and 390 × 844; manual/rapid navigation, title-cover association,
  stable sizing and zero console errors passed. Reduced motion is covered by the focused automated
  test and was not separately performance-profiled in a Production browser.
- GitHub Actions run `38586750058` for the exact release SHA: Backend and Frontend PASS.

## Release and Production evidence

`origin/main` resolves to the exact release commit. GitHub Production deployment `7069199596`
completed successfully for that SHA and targets the Vercel deployment URL
`https://buddy-web-ver2-n5hhkpzst-dat1507s-projects.vercel.app`. The public alias returns 200 and
serves bundle `index-DfxH7DYv.js`; the bundle contains the Admin Events route and no EN/DE Audience
label. Effective behavior proves both Admin and Public Event surfaces are enabled, although the
provider's raw environment-variable values were not independently exported.

Read-only Production checks at 2026-10-14 22:17–22:18 Asia/Saigon found:

- EN and DE public Event APIs each returned the same two `PUBLISHED`, cover-ready Events: Kawazo
  (`5a3c57aa-b676-4df3-92cd-414c82ea2c13`) and Buddy Recruitment
  (`98951257-9edc-4ed2-a64f-f5ea464ef771`).
- Production OpenAPI no longer exposes `visibility` in `EventDraftCreate` or as an Admin list
  filter.
- The live Landing Slider rendered those same two Event links in EN and DE; previous/next controls
  remained usable through rapid input, 390 × 844 had no horizontal overflow, and browser console
  error/warning capture was empty.
- The Production Admin create form rendered no Audience field. It was inspected read-only; no
  draft was submitted and no publish workflow was executed.

Available browser profiles already had an authenticated session, so anonymous frontend rendering
was not independently repeated by signing the user out. The same unauthenticated public endpoints
returned 200 with the two eligible Events, and the Slider's rendered dataset matched them. No Event,
user, registration setting, Storage object, database row, provider configuration, DNS record or
feature flag was modified during Production verification.

## Preserved evidence gaps

- Render deployment identity/source SHA was not exposed by the available read-only provider access;
  the new backend behavior and OpenAPI contract are directly visible, but the provider deployment
  record is not independently claimed.
- Production Alembic revision `0022` was not independently queried.
- Production create/publish was intentionally not exercised because it would mutate Event data.
- Production reduced-motion and touch-gesture frame timing were not separately profiled; focused
  automated coverage and local browser verification passed.
