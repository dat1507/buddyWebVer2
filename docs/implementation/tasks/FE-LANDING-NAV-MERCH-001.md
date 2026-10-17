# FE-LANDING-NAV-MERCH-001 — Merchandise and Landing navigation

**Assigned:** 2026-10-17 (Asia/Saigon), owner pasted task request.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.

Restore Merchandise alongside the five Campus Resources cards using current shared styling.
Show EN `Coming Soon` / DE `Demnächst verfügbar` with no purchase action, route or commerce
implementation. Six cards use 3×2 desktop, two tablet columns and one mobile column. Preserve
all four confirmed external destinations, Events Recap pending state and section title/description.

Rename navbar Resources / Ressourcen, preserve `#features`, and add Events / Veranstaltungen
pointing to the existing slider. Use one unique `#events` section anchor in static and live
loading/error/empty/populated states. Retain sticky-navbar offset, cross-route/reload navigation,
mobile drawer close, focus and reduced motion. Do not change Event fetching or slider behavior.

Focused sources: BenefitsGrid, Navbar, EventsSlider and LiveEventsSection section attributes,
Landing hash handler, EN/DE locales and their existing component/assembly tests. Reuse current
knowledge protocol and frontend guide. Validate focused tests, TypeScript, ESLint, Prettier,
production build and local desktop/tablet/mobile behavior before a local commit on `main`.

Initial worktree clean at `54e3733`. Owner authorizes code/tests/knowledge commit together;
no Production/backend/database/API/auth changes, push or deployment.

## Verified outcome — 2026-10-17

Merchandise is the sixth card, using ShoppingBag and localized unavailable copy/status. It has
no link, button, tab stop or purchase behavior. Desktop is a regular 3×2 grid. Existing cards,
section heading/description and four external URLs remain intact. The section eyebrow now owns
its Campus Resources localization rather than inheriting the shorter navigation label.

Navbar uses Resources / Ressourcen and Events / Veranstaltungen. Events targets `/#events`;
Resources retains `/#features`. Full desktop navigation starts at 1280px; the existing drawer
covers smaller widths after a 1024px German overflow was found and corrected. All existing links
and account actions remain available. EventsSlider and live placeholder states only gain section
ID/scroll margin; query, selector, eligibility, order and carousel logic are unchanged.

Focused regression: five files / 45 tests PASS; final Navbar rerun 15 PASS. TypeScript, affected
ESLint/Prettier and production build PASS (existing bundle-size advisory). Build initially caught
unsupported Testing Library `exact` test options; removed without changing assertions. Brave
1440×1000 / 768×1024 / 390×844 confirms 3/2/1 card columns; the corrected 1024px navbar has no
overflow. EN/DE statuses/navigation, mobile drawer close, `/login` → `/#events`, refresh,
80px section clearance and reduced-motion `transition-property: none` / auto scroll verified.
Existing local auth bootstrap warning remains because the API is not running; no authenticated
session or Production acceptance is claimed. See [validation](../validation.md).
