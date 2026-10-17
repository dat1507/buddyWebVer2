# FE-LANDING-ORDER-001 — Landing display order

**Assigned:** 2026-10-17 (Asia/Saigon), owner request.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.

Reorder the shared Navbar array to Home, Events, About, Resources, then retain Community,
Contact and Survival Book in their existing relative order. Reorder the Resources array to
Merchandise, Events Recap, Library, Sports Hall, International Office, Dormitory Service.
Preserve all styling, localized content, anchors, offsets, external URLs, unavailable states
and existing functionality. No CSS ordering, purchase action or Events Recap implementation.

Focused files: Navbar and BenefitsGrid source/tests, existing Landing assembly test and frontend
knowledge. Validate EN/DE desktop/mobile order, responsive 3/2/1 columns, keyboard order, links,
focused tests, TypeScript, ESLint, Prettier and production build. Commit locally on current main;
no push/deployment/backend/database/API/Production change. Initial worktree clean at `a08c64d`.

## Verification — 2026-10-17

Only two source array orders changed. Focused Navbar/Resources/Landing tests: 3 files / 32 PASS.
TypeScript, affected ESLint/Prettier and production build PASS; existing large-bundle advisory.
Brave EN/DE at 1440×1000, 768×1000 and 390×1000 confirmed requested DOM/visual order,
3/2/1 columns and zero horizontal overflow. Both localized mobile menus retain the requested
Navbar order; Events navigation closes the drawer. Keyboard Tab from Library reaches Sports
Hall; resource href/target/rel values remain exact. Merchandise is Coming Soon / Demnächst
verfügbar without an action; Events Recap remains UI prepared — functionality pending.
No style, translation, section-anchor, offset or behavioral source change. Existing local auth
bootstrap connection warning remains; no authenticated account or Production verification.
[Validation](../validation.md) records the bounded acceptance. Local commit only.
