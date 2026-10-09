# Phase 2 post-deployment roadmap

**Updated:** 2026-10-09
**Status:** FIRST TWO FEATURES DEPLOYED; PROFILE AUTHENTICATED VISUAL GATE OPEN

## Controlling owner decision

The first independent Phase 2 development tasks are:

1. `FE-LANDING-BG-001` — Landing `#home` background slideshow and removal of the Facebook-linked
   Welcome card.
2. `FE-PROFILE-HOME-UNI-001` — User Profile Home University display/edit using the existing API
   field, with no matching impact.
3. Event system.
4. Event Calendar.
5. VGU Map.
6. AI Assistant.
7. Merchandise.
8. Remaining enhancements.

Technical dependencies inside each later feature remain unchanged. This priority decision permits
local development of the two isolated frontend tasks before Phase 1 closure. It does not close,
downgrade or hide Backup/DR, `PROD-001`, `SEM-008` or residual `ACCEPT-001` blockers.

The owner explicitly approved the `origin/main` push and Vercel Production deployment on
2026-10-09. That approval was consumed for commit `2f6f8c8`; it does not authorize unrelated future
deployments or Production/provider/database changes.

## Current implementation boundary

### `FE-LANDING-BG-002`

- Correct only the performance/transition lifecycle of the existing `#home` slideshow.
- Preserve the five assets, their order, Hero content/design and all unrelated surfaces.
- Require decoded-next-image gating, stable opacity-only double buffering, hidden-tab timer pause,
  focused regression tests and three-loop desktop/mobile browser evidence before release closure.

### `FE-LANDING-BG-001`

- Only `#home` receives the slideshow; the Event slider and all other pages/sections are unchanged.
- Use only the five owner-supplied files under `C:\Users\phuoc\Downloads\background`.
- Preserve a stable documented order, optimize local copies, load only the current/next image,
  crossfade without layout shift, respect reduced motion and retain a dark fallback/contrast layer.
- Remove only the Facebook-linked `Welcome to VGU Buddy` card instance from the Landing hero.

### `FE-PROFILE-HOME-UNI-001`

- `home_university` already exists in the database, authenticated Profile response/update schema,
  service allowlist, frontend parser and Admin detail.
- Add optional User Profile display and edit UI using the existing field and 200-character contract.
- Do not add a migration, backend route, browser storage, onboarding requirement, matching field or
  recommendation weight.

## Release boundary

Both features are deployed. Landing desktop/mobile/transition inspection passed directly against
Production. Home University automated and deployed-bundle verification passed, while authenticated
Profile display/edit/save/reload remains an explicit manual gate and is not recorded as PASS.

The release preserves all open Phase 1 blockers. After authenticated Profile visual acceptance and
a separate implementation instruction, the next Phase 2 product task in the owner-approved order
is the Event system.
