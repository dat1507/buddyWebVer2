# Frontend implementation

React 19, TypeScript, Vite, React Router, TanStack Query, Zustand, Tailwind and i18next are
declared in [package.json](../../../apps/web/package.json). Version ranges describe declared
dependencies; the lockfile determines installed versions. These technologies are observed
choices; a complete record of the author's original alternatives is unavailable.

## Where to read

| Concern            | Source                                                                                                                                           | Meaning                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Boot/providers     | [main.tsx](../../../apps/web/src/main.tsx)                                                                                                       | Mounts app and providers                                           |
| Route ownership    | [App.tsx](../../../apps/web/src/App.tsx)                                                                                                         | Public, USER and ADMIN layout boundaries                           |
| User delivery map  | [user-routes.ts](../../../apps/web/src/routes/user-routes.ts)                                                                                    | Real pages versus assistant/campus placeholders; profile readiness |
| Admin delivery map | [admin-routes.ts](../../../apps/web/src/routes/admin-routes.ts)                                                                                  | Monitoring/users/semesters/Events versus undelivered modules       |
| Session            | [session-client.ts](../../../apps/web/src/features/auth/session-client.ts), [store](../../../apps/web/src/stores/auth-store.ts)                  | Bootstrap, CSRF recovery, refresh/logout and memory-only identity  |
| HTTP               | [api.ts](../../../apps/web/src/lib/api.ts)                                                                                                       | Credentialed requests, timeout, abort and safe errors              |
| Language           | [i18n.ts](../../../apps/web/src/i18n.ts), [EN](../../../apps/web/src/locales/en/common.json), [DE](../../../apps/web/src/locales/de/common.json) | Translation keys and locale behavior                               |

Routing decides which component to display. `RoleGuard` waits for verified session state;
`ProfileReadinessGate` keeps incomplete profiles in onboarding. Neither replaces API checks.
Admin overview is not proof every displayed module has a backend: the registry explicitly
marks placeholders. Audit log storage exists even though the Admin audit-log page is a placeholder.

## Server state and error handling

TanStack Query caches fetched responses; feature hooks own keys and invalidation. Zustand
keeps current auth state without persisting credentials. Private cache cleanup on logout or
account switching prevents a previous account's data appearing in another session.

The common HTTP client requires a configured `VITE_API_URL`, accepts only local absolute
paths, includes cookies, requires a CSRF token on mutations and aborts after 15 seconds.
It converts status codes into bounded error categories and allowlisted domain reasons.
It deliberately does not retain raw response bodies or raw fetch diagnostics in errors.

## Feature composition

[MatchingPage](../../../apps/web/src/pages/user/matching-page.tsx) composes recommendations,
invitation controls and Buddy information from feature clients/hooks. The selected profile
dialog uses the existing safe recommendation projection, not an unrestricted profile endpoint.
See [Matching workflow](../WORKFLOWS.md).

[UserEventsPage](../../../apps/web/src/pages/user/user-events-page.tsx) and Landing use
[useEventSliders](../../../apps/web/src/features/events/queries/use-event-sliders.ts), a
locale-keyed query that refetches every 60 seconds. The API repository validates its response;
the shared selector limits presentation to five. Detail return context is a validated query
marker so dashboard-origin navigation survives refresh without becoming an arbitrary redirect.
Registration is optional; an absent usable URL does not remove a card.

## Landing, responsive design and accessibility

[Landing page](../../../apps/web/src/pages/public/landing-page.tsx) composes the public
sections. Hero transitions were corrected to avoid swapping an image underneath a visible
layer. Static bundled Event posters remain the public-flag-OFF path. Flag-ON uses canonical
data; it does not quietly replace errors with fake live Events.

The baseline About walkthrough uses labeled CSS dashboard illustrations and accessible tabs,
keyboard navigation and reduced-motion behavior. They illustrate product concepts rather than
embedding an authenticated dashboard. The old demo CTA/video was removed before this baseline.
Sticky-navbar offset is preserved for `#about`, including direct refresh.

[Events Showcase](../../implementation/tasks/FE-LANDING-SHOWCASE-001.md) keeps the existing Upcoming
Events slider as the primary content, including its flag-OFF static path and flag-ON query/states.
[EventsExploreMore](../../../apps/web/src/components/landing/events-explore-more.tsx) follows
that branch before About: Previous Events Recap then Merchandise
[wide feature cards](../../implementation/tasks/FE-EXPLORE-WIDE-CARDS-001.md) now align with the slider
max-w-7xl container, side by side from 640px and stacked below. Responsive 24–40px padding,
36–40px icons and equal-height cards keep bottom actions aligned, including wrapped EN/DE
status text. The wrapper reduces excess gap by 16/24px within the slider bottom padding;
slider dimensions and query/cache/eligibility/order logic remain unchanged. Dark/orange styling,
focus rings and reduced-motion-safe hover remain; no images or dependencies were added.

Public routes `/events/recap` and `/merchandise` use
[CommunityComingSoonPage](../../../apps/web/src/pages/public/community-coming-soon-page.tsx)
inside PublicLayout, independent of Event flags/auth. Static Recap route takes precedence over
Event detail matching. EN/DE placeholders preserve language selection and link Back to Events
at `/#events`; existing SPA hosting rewrite supports direct URL refresh. Both are **Coming Soon —
functionality pending**, with no real recap/gallery/commerce/API implementation.

[Campus Resources](../../../apps/web/src/components/landing/benefits-grid.tsx) now contains
Library, Sports Hall, International Office and Dormitory Service in that DOM/visual order.
Desktop/tablet use two columns, mobile one; shared cards retain equal-height rows, official
owner-confirmed URLs, secure external tabs, focus rings and 44px links.
[Photo cards](../../implementation/tasks/FE-LANDING-RESOURCE-IMAGES-001.md) use four owner-supplied images
from `Downloads/Campus Resources`, optimized into `src/assets/campus-resources/*.webp`.
The task records source mapping/dimensions/bytes. Reserved 16:9 CSS cover containers replace
decorative icons; group/dormitory positions preserve subjects. Intrinsic dimensions, native
lazy loading, async decoding and EN/DE descriptive alt text accompany rounded image clipping.
Original files remain unchanged; no dependency or replacement image was introduced. Heading/description,
EN/DE copy and `#features` 80px scroll margin remain. Recap and Merchandise moved to Explore More.

Navbar order remains Home, Events, About, Resources, Community, Contact, Survival Book (EN/DE).
Events targets the existing `/#events` slider anchor in all live states, with 80px offset and
cross-route/direct-refresh resolution. Full navbar starts at 1280px, with its accessible drawer
below. No Campus Resources API, auth dependency or database state is introduced.

[Footer](../../../apps/web/src/components/layout/footer.tsx) uses the
[Minimal Branding layout](../../implementation/tasks/FE-LANDING-FOOTER-001.md): branding and preserved
Facebook/Instagram links alongside Get in Touch, stacking on mobile. Quick Links and Support
were removed. EN/DE Contact Us / Kontaktiere uns links to `mailto:vgubuddy@vgu.edu.vn`; no form
or server email feature exists. Logo proportions, dynamic copyright year, language availability,
dark background and orange focus rings remain. Socials use secure new tabs, 44px targets and
reduced-motion-safe transitions. Footer retains `#contact` with 80px scroll margin.

Responsive verification records cover desktop/tablet/mobile widths and horizontal overflow;
they are scoped to each task, not evidence that every route passes every viewport. UI tests
check semantic behavior and focus/role contracts. Preserve reduced motion, image decoding,
keyboard focus and EN/DE strings when extending these sections.

History and acceptance: [About task](../../implementation/tasks/FE-LANDING-ABOUT-001.md),
[CTA task](../../implementation/tasks/FE-LANDING-CTA-001.md),
[slideshow task](../../implementation/tasks/FE-LANDING-BG-002.md),
[User Events task](../../implementation/tasks/FE-USER-EVENTS-001.md).
