# FE-LANDING-RESOURCE-IMAGES-001 — Campus Resources images

**Assigned:** 2026-10-17 (Asia/Saigon), owner supplied local image directory.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.

Add descriptive top images to the four existing resource cards, retaining order, copy, official
URLs, EN/DE and 2×2 desktop/tablet / one-column mobile grid. Use supplied library.jpg,
sport_hall.jpg, international_office.jpg and dormitory.webp after inspecting their content.
Optimize required copies to WebP using existing bundled tooling; originals remain unchanged.
Use consistent 16:9 CSS cover containers, intentional subject-safe positions, intrinsic dimensions,
native lazy loading, localized alt text and existing focus/reduced-motion styling. No downloads,
generated replacements, dependencies or unrelated section/backend/API/auth/data changes.

Focused scope: BenefitsGrid, four optimized assets, EN/DE alt keys, focused card/Landing tests,
frontend knowledge and control-plane records. Validate dimensions/bytes/crops, responsive browser
rendering, exact links, focused tests, TypeScript, ESLint, Prettier and production build.
Initial main clean at `9309da7`; local commit authorized, no push or Preview/Production deployment.

## Asset mapping and optimization — 2026-10-17

Source directory: owner-supplied `Downloads/Campus Resources`. Filenames and all four original
images were visually inspected. Library shows the atrium/stairs, Sports Hall uses the supplied
outdoor courts photo (alt text describes courts), International Office uses the group beside the
blue Einstein statue, and Dormitory shows the residential building/entrance. Mapping is unambiguous.

Assets live in `apps/web/src/assets/campus-resources/`:

| Card / source                                   | Original dimensions / bytes | Optimized asset           | Output dimensions / bytes |
| ----------------------------------------------- | --------------------------- | ------------------------- | ------------------------- |
| Library / library.jpg                           | 1201×800 / 185,516          | library.webp              | 1201×800 / 119,690        |
| Sports Hall / sport_hall.jpg                    | 2048×1152 / 452,907         | sports-hall.webp          | 1440×810 / 185,312        |
| International Office / international_office.jpg | 2045×1202 / 895,601         | international-office.webp | 1440×846 / 152,734        |
| Dormitory / dormitory.webp                      | 2500×1665 / 359,178         | dormitory.webp            | 1440×959 / 119,024        |

Bundled Pillow: EXIF transpose, RGB conversion, Lanczos thumbnail max 1440px (no upscaling),
WebP quality 82/method 6; no metadata copied or dependency installed. Total 1,893,202 → 576,760
bytes (69.5% smaller). SHA-256 checks before/after processing confirmed source bytes unchanged.
Only the four optimized copies are committed; no generated replacement or alternate variant.

## UI and verification

Images replace the decorative top icons. Existing shared cards clip the top image to rounded
corners, with reserved 16:9 containers and CSS object-cover, never stretched. Positions are
center for Library/Sports, 50% 40% for the group portrait, and 50% 65% for Dormitory. Visual
inspection preserves all faces, statue, library subject and dormitory building/entrance.
Intrinsic width/height, lazy loading and async decoding accompany meaningful EN/DE alt text.
Four-card order, copy, official URLs, external-link security, spacing tokens and 2/2/1 columns
remain. Equal-height grid rows and flex content align actions; mobile images are ~192px high.
No image scaling animation; existing hover transitions disable for reduced motion.

Two focused files / 15 tests PASS. TypeScript, affected ESLint/Prettier and production build
PASS; build emits four hashed WebP assets, existing bundle advisory remains. Brave EN/DE
1440×1000, 768×1000 and 390×1000: decoded correct images, constant 16:9, equal card heights,
zero overflow, correct alt text. Native lazy-loading check: all four unloaded at Home with
352.35px reserved height, all loaded after Resources navigation with identical height. Keyboard
Library → Sports shows orange focus ring; reduced-motion card transitions all none. Overrides
reset. Existing local API bootstrap warning remains; no account or Production acceptance.
[Validation](../validation.md) contains the bounded result. No push or deployment.
