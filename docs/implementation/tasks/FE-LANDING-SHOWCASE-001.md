# FE-LANDING-SHOWCASE-001 — Events Showcase and four campus resources

**Assigned:** 2026-10-17 (Asia/Saigon), owner pasted contract.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.

Keep Upcoming Events slider, static/live branching, query/selection/eligibility/cache, transitions,
dimensions and states intact. Compose Explore More immediately below it with Previous Events Recap
then Merchandise secondary cards. Link to public localized Coming Soon pages `/events/recap` and
`/merchandise`, both with Back to Events → `/#events`. Preserve PublicLayout and hosting SPA rewrite.
No recap data/gallery/API or products/cart/checkout/payment functionality.

Reduce Campus Resources to Library, Sports Hall, International Office, Dormitory Service in that
order. Preserve four exact official URLs, copy/icons, #features, heading/description and Navbar.
Use existing Card/Typography styling in a 2×2 desktop/tablet, one-column mobile layout.

Focused sources: Landing composition, BenefitsGrid, new Explore More/Coming Soon UI, App public
routes, EN/DE locales, focused assembly/Resources/route and existing slider/flag regression tests.
Verify links, direct refresh, return hash, EN/DE, keyboard/reduced motion, responsive layout,
TypeScript, ESLint, Prettier and build. Initial main clean at `f666345`.
Commit source/tests/knowledge together locally; no push, Preview/Production deployment or
backend/database/auth/API/Production change. Both future business features remain pending.

## Verified outcome — 2026-10-17

Landing now composes EventsExploreMore immediately after the existing static/live slider branch,
before About. The slider remains the primary section; Explore More uses a smaller heading,
max-w-4xl container and two compact icon cards (Recap then Merchandise). Cards stack below 640px.
The existing slider/live-section/event-feature source bytes are unchanged. There is one #events
anchor with the accepted offset; loading/error/empty/populated states and first-five logic remain.

Campus Resources contains only Library, Sports Hall, International Office, Dormitory Service,
using the same official URLs/copy/icons/external-link attributes in two columns from 640px and
one below. The heading/description/#features and Navbar/Footer remain intact.

PublicLayout routes /events/recap and /merchandise use one lightweight localized placeholder
component. Static Recap route is outside the Event launch flag and outranks the dynamic detail
route/wildcard; both work with public Events OFF and ON. Back to Events returns to /#events.
EN/DE status, titles/descriptions and navigation use existing i18next selection. The existing
SPA catch-all hosting rewrite supports deep links without configuration changes. Both business
features remain **Coming Soon — functionality pending**; no galleries, real recaps, products,
purchase controls, API calls or auth requirements were added.

Verification: 6 focused files / 44 PASS; public Events ON route/flag suite 2 files / 15 PASS.
TypeScript, affected ESLint/Prettier and production build PASS; existing large-chunk advisory.
Brave local EN/DE desktop/tablet/mobile (1440×1000, 768×1000, 390×1000) confirms resource 2/2/1
columns, secondary cards 2/2/1 and no horizontal overflow. Both routes opened from their cards,
refreshed directly and returned to #events; return offset measured 80px below ~65px Navbar.
Keyboard Tab moves Recap CTA to Merchandise CTA with visible orange focus. Reduced-motion
classes retained; no animation was added to placeholders. Live query/selection/state paths are
covered by focused regression and flag-ON tests; browser used the local static Event path.
Existing local API bootstrap warning persists; no account or Production acceptance is claimed.
Local sandbox preview was unreachable; local-only unsandboxed server enabled browser checks.
[Validation](../validation.md) records acceptance. No push or deployment.
