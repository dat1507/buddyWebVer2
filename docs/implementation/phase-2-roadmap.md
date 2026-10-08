# Phase 2 post-deployment roadmap

**Updated:** 2026-10-08
**Status:** OWNER-APPROVED EXECUTION ORDER; PRODUCTION RELEASE NOT APPROVED

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

Local `main` commits are approved. Push to `origin/main`, a Vercel Production build/deployment and
all other Production/provider/database changes still require a separate explicit owner approval.

## Current implementation boundary

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

The first two tasks are locally implemented with automated verification passing. Direct desktop,
mobile, transition and authenticated Profile visual inspection remains a manual gate because the
available computer-use browsers could not reach the terminal-local Vite server. This limitation is
not recorded as a visual PASS.

Implementation completion is not Production acceptance. Release instructions stop before
push/deploy and preserve all open Phase 1 blockers. After manual visual acceptance and a separate
release decision, the next Phase 2 product task in the owner-approved order is the Event system.
