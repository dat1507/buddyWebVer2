# FE-LANDING-ABOUT-001 — Landing About and How It Works

**Date:** 2026-10-17
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED
**Authorization:** Owner supplied Landing About UI/UX request; local implementation, verification and commit on main. No push/deployment.

## Contract

Replace the existing About introduction and three cards; retain group.jpg, dark/orange identity and #about. Add three accessible, keyboard-operated steps for Profile, Discover & Match, Connect & Explore, with EN/DE copy and reduced-motion support. Use clearly labeled CSS illustrations derived from existing dashboard UI when authentic screenshots are unavailable. Preserve Features, final CTA and all application workflows. No backend, API, account, database or provider changes.

## Focused source and verification

- apps/web/src/components/landing/about-section.tsx and about-section.test.tsx
- apps/web/src/components/landing/how-it-works.tsx
- apps/web/src/pages/public/landing-page.tsx and landing-page.test.tsx
- apps/web/src/components/landing/hero-section.tsx; apps/web/src/index.css
- apps/web/src/locales/{en,de}/common.json
- UI references only: pages/user/profile-page.tsx, matching-page.tsx, user-events-page.tsx; features/matching/current-buddies-section.tsx.
- TypeScript, affected ESLint/Prettier, focused About/Landing/Features/CTA tests, production build, responsive browser checks when available.

## Evidence

2026-10-17: TypeScript, affected ESLint and production build PASS; existing large-chunk advisory only. Focused About/Landing/Features/CTA: 4 files / 23 tests PASS. Tests cover EN/DE steps, arrows/Home/End/wrapping, ARIA state, Learn More href, direct hash mount and unchanged section order. Features and CTA source unchanged.

Local Brave checks at 1440×900, 768×1024 and 390×844: responsive layout and zero horizontal overflow; matching and accepted-Buddy illustrations update, German rendering and refreshed /#about resolve above content without sticky-header occlusion. Existing local auth bootstrap reports a connection failure; no account or Production session used. Reduced motion verified by CSS inspection (no animation; automatic anchor scrolling), not browser emulation. Initial sandbox Vite temporary-file/socket failures were resolved by running checks and preview outside the sandbox. No new dependencies, screenshots or personal data.

Commit on local main only; no push/deployment or Production changes.
