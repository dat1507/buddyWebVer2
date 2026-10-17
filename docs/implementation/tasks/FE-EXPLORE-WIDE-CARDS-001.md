# FE-EXPLORE-WIDE-CARDS-001 — Explore More wide feature cards

**Assigned:** 2026-10-17 (Asia/Saigon), owner selected Wide Feature Cards.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.

Expand Explore More to the Landing/Events max-w-7xl container, two equal desktop cards with
24–32px gap, 32–40px desktop padding and prominent 36–40px icons. Use natural/minimum heights,
aligned bottom actions and existing dark/orange focus/hover styling with reduced-motion support.
Keep the centered heading/copy, Recap then Merchandise order, Coming Soon status, routes,
direct refresh and Back to Events. Preserve Upcoming slider source/dimensions/data/controls,
Events anchor, EN/DE, other sections and public layout. No images/dependencies/business features.

Focused scope: EventsExploreMore, existing Coming Soon/Landing tests, frontend knowledge and
control-plane records. Check desktop/tablet/mobile alignment/overflow, keyboard/focus, reduced
motion, navigation/refresh, tests, TypeScript, ESLint, Prettier and build. Initial main clean
at `6da21ac`. Local code/knowledge commit only; no push or Preview/Production deployment.

## Verified outcome — 2026-10-17

Explore More now matches the slider's max-w-7xl outer content container. Desktop cards use
32px gap, 32–40px padding, 40px icons and a soft 288px minimum content height; no fixed card
height. Header icons/titles sit together, descriptions retain their exact copy, and bottom
footers align both actions. Below 1024px the footer stacks its availability status with reserved
space, keeping EN/DE actions aligned; padding/icons reduce to 24–28px / 36px. Two columns from
640px, one below. Merchandise Coming Soon remains visible, with navigation enabled.

The wrapper reclaims 16px mobile / 24px larger-screen space from the preceding slider's empty
bottom padding; slider source and geometry are unchanged. Centered subsection heading, divider,
secondary visual hierarchy and bottom spacing to About remain. No route/localization, assets,
resource cards, Navbar/Footer, Event data or other application source changed.

Final tests: Coming Soon/Landing, 2 files / 16 PASS (including status preservation, both route
round trips and EN/DE direct entry). TypeScript, affected ESLint/Prettier and build PASS;
existing bundle advisory. Brave EN/DE at 1440×1000, 768×1000 and 390×1000 confirmed equal card
widths/heights, aligned action offsets, readable wrapping and zero overflow. At 1440px both
containers are 1280px; cards are 624×~290px, icons 40px. Tablet EN/DE heights ~262/~310px;
mobile ~254/~302px (natural content growth). Both routes refreshed successfully and returned
to #events at 80px below ~65px Navbar. Keyboard Recap → Merchandise shows orange focus rings;
reduced-motion transitions are none. Temporary browser settings reset.

Existing local API bootstrap warning remains; no account or Production acceptance.
An unrelated root TUN_9944.jpg deletion appeared during execution and is preserved/excluded
from the task commit. [Validation](../validation.md) records the bounded acceptance.
Local commit only; business Recap/Merchandise functionality remains pending.
