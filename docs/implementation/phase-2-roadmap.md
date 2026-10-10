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

The release preserves all open Phase 1 blockers. The owner separately selected the Event system and
later authorized a rollback-gated controlled Production code deployment after isolated local
acceptance. This does not close the remaining Profile acceptance, authorize Production write tests
or authorize the Event launch flag.

## Event system continuation — 2026-10-09

- The owner separately selected the Event lane. The local canonical chain through `FE-014B` is
  implemented; the Landing slider is derived from canonical published Events rather than a separate
  slider database/admin page.
- Dynamic public/Admin routes remain behind `VITE_EVENTS_LAUNCH_ENABLED`. Production remains on the
  static five-poster carousel during the approved code deployment and smoke test; enabling the
  canonical Event surfaces still requires explicit launch approval.
- `EVS-007` is DONE: supported Python 3.12 regression passes 1,408 backend tests with 37 skips,
  focused Event backend passes 121 tests and frontend passes 774 tests. Landing caps presentation
  at the owner-selected first five canonical results; the backend bounded query cap remains 12.
- The owner replaced cloud-Staging acceptance with isolated local A–E, Production rollback
  preflight, controlled code deployment with the flag OFF and safe Production smoke. The reason is
  the one-database Upstash Free limit and the decision not to add a paid cloud service. All original
  security/quality criteria remain; Production writes are not included.
- Isolated local A–E completed PASS on 2026-10-10: 79 API assertions plus real browser acceptance,
  followed by backend 1,408 PASS / 37 SKIP and frontend 84 files / 774 PASS. Production preflight is
  complete with executable rollback. Application SHA `e2ef4c0` is deployed to Vercel/Render;
  GitHub CI and read-only Production smoke passed while the Event flag remained OFF. No Production
  Event data write or launch action occurred.

## Event activation split — 2026-10-11

- `EVENT-FLAG-SPLIT` supersedes the shared frontend launch switch with independent strict Admin and
  public switches. Missing/invalid values are OFF, and the legacy switch is ignored.
- Admin OFF consistently hides list/create/edit navigation and overview metrics. Public OFF retains
  the unchanged five-poster static Landing with no live slider request and hides public/User Event
  surfaces. Existing role guards and backend authorization remain unchanged.
- Resolver, route/navigation/dashboard/Landing tests, all four flag combinations, missing/invalid/
  legacy cases, the 85-file/788-test frontend suite and all four production builds pass locally.
- The controlled release keeps both Production switches OFF and stops before Admin activation,
  Production Event writes or public-live activation.
