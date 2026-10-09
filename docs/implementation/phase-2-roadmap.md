# Phase 2 post-deployment roadmap

**Updated:** 2026-10-09
**Status:** LANDING ACCEPTED; PROFILE DISPLAY ACCEPTED / EDIT-PERSISTENCE GATES OPEN; EVENT LOCAL IMPLEMENTATION COMPLETE

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

The owner explicitly approved the original `origin/main` push and Vercel Production deployment on
2026-10-09, then separately approved the corrective `FE-LANDING-BG-002` release. Those approvals
were consumed by commits `2f6f8c8` and `c2fbaf1`; they do not authorize unrelated future deployments
or Production/provider/database changes.

## Current implementation boundary

### `FE-LANDING-BG-002`

- Status: DONE / PRODUCTION VERIFIED from `c2fbaf1` and deployment `6952736000`.
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
Production and the owner confirmed the corrected transition is smooth. The owner also confirmed
that Home University displays correctly in the authenticated Production Profile. The separate
edit/save/reload/clear/max-length acceptance remains open, so the Profile task is not DONE.

The release preserves all open Phase 1 blockers. The owner has now separately selected the Event
system for local implementation; this does not close the remaining Profile acceptance or authorize
an Event push, Staging mutation, Production launch flag or deployment.

## Event system continuation — 2026-10-09

- The owner separately selected the Event lane. The local canonical chain through `FE-014B` is
  implemented; the Landing slider is derived from canonical published Events rather than a separate
  slider database/admin page.
- Dynamic public/Admin routes remain behind `VITE_EVENTS_LAUNCH_ENABLED`. Production remains on the
  static five-poster carousel until `EVS-007`, deployed Staging `ACCEPT-EVENT-001` and explicit
  release approval pass.
- Event-focused backend tests pass 96/96 and frontend tests pass 772/772. `EVS-007` remains open for
  two unrelated Python 3.14 WebSocket `TestClient` teardown failures in the full backend suite.
