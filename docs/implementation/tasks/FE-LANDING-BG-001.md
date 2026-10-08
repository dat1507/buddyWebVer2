# FE-LANDING-BG-001 — Landing background slideshow

**Feature group:** Landing page
**Priority:** Phase 2 Priority 1
**Status:** IMPLEMENTED — AUTOMATED PASS / MANUAL VISUAL GATE OPEN
**Dependencies:** Existing `FE-019` Landing assembly and owner-supplied local image set.

- **Objective:** add an automatic, continuously looping background slideshow only to Landing
  `#home`, and remove the Facebook-linked Welcome card.
- **Scope:** audit/optimize supplied images, stable ordering, current/next lazy loading, 7-second
  display, 1-second opacity crossfade, reduced-motion static fallback, dark contrast overlay, image
  failure fallback and removal of the one Welcome card instance.
- **Out of scope:** Event slider changes, global backgrounds, routing/auth changes, redesign,
  third-party images, animation dependency or Production deployment.
- **Relevant modules:** `hero-section.tsx`, focused Landing components/tests, local Landing assets.
- **Frontend changes:** isolated Hero background component/assets and Welcome-card removal.
- **Backend changes / Database changes:** none.
- **Security:** repository-local distributable images only; strip metadata; no remote image URL.
- **Acceptance:** five supplied images are audited; chosen images load without flash/layout shift;
  loop/crossfade/reduced motion work; text/buttons retain contrast; Facebook card/link is absent;
  no other section/page changes.
- **Tests:** focused component/Landing tests, TypeScript, ESLint, Prettier, build and desktop/mobile
  browser verification.
- **Complexity:** M.
- **Production impact:** frontend assets/bundle only after separate push/deploy approval.
- **Manual actions:** owner reviews local screenshots and separately approves any Production push.

## Implementation evidence — 2026-10-08

- All five supplied images decoded successfully, were visually suitable as campus context and were
  retained; no supplied image was rejected. The source set mixes landscape ratios, so `object-cover`
  uses intentional center cropping while the dark overlay protects copy readability.
- Metadata-stripped WebP copies were created without modifying the originals. The fixed sequence is:

  | Order | Source audit | Optimized artifact |
  | --- | --- | --- |
  | 1 | `a1-17749513503351091833885.webp`, 1920x1280, 3:2 WebP, campus exterior | `01-campus-exterior.webp`, 1920x1280, 271,922 bytes |
  | 2 | `truongvietduc-pr-1786358957821.webp`, 1020x574, ~16:9 WebP, campus aerial | `02-campus-aerial.webp`, 1020x574, 141,978 bytes |
  | 3 | `online-information-skill.jpg`, 2560x1920, 4:3 JPEG, campus garden | `03-campus-garden.webp`, 1920x1440, 359,220 bytes |
  | 4 | `banner-dds.jpg`, 1520x450, panoramic JPEG, campus architecture | `04-campus-architecture.webp`, 1520x450, 36,580 bytes |
  | 5 | `3a-min-1142x800.jpg`, 1142x800, landscape JPEG, library | `05-campus-library.webp`, 1142x800, 80,642 bytes |
- The optimized set is 890,342 bytes. Only the current/next image pair is mounted, with a 7-second
  display, 1-second opacity crossfade, cleanup on unmount, reduced-motion static fallback and black
  failure/paint fallback. The Hero keeps its dimensions and adds dark overlays for text contrast.
- The Facebook-linked Welcome card was removed. The static Event slider and all non-Hero sections
  were left unchanged.
- Focused automated tests, lint, typecheck, formatting and production build pass. Direct desktop,
  mobile and animation visual inspection remains an explicit manual gate because both available
  computer-use browser surfaces timed out when accessing the terminal-local Vite server.
