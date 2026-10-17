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

[Campus Resources](../../implementation/tasks/FE-LANDING-RESOURCES-001.md) replaces Benefits
with six icon cards after the [Merchandise/navigation update](../../implementation/tasks/FE-LANDING-NAV-MERCH-001.md):
Display order after the [ordering task](../../implementation/tasks/FE-LANDING-ORDER-001.md) is
Merchandise, Events Recap, Library, Sports Hall, International Office, Dormitory Service.
Merchandise is unavailable, with Coming Soon / Demnächst verfügbar and no purchase interaction. The owner confirmed all four official destinations; the source array owns those URLs.
Resource links open secure new tabs with localized labels, focus rings and 44px touch height.
Events Recap is **UI prepared — functionality pending** with no action or route. Navbar/footer
share EN/DE Resources / Ressourcen copy; `#features` remains the anchor, uses 80px scroll margin and
resolves after mount/direct refresh. Desktop uses a 3×2 card grid, tablet uses two columns
and mobile one; equal-height rows and reduced-motion-safe border/shadow hover use shared tokens.
Navbar desktop/mobile order is Home, Events, About, Resources, Community, Contact, Survival Book
(with EN/DE labels); shared arrays determine DOM/keyboard and responsive card order.
Navbar Events / Veranstaltungen targets `/#events` on the existing slider and live loading/error/empty
states, with 80px scroll margin and direct-refresh/cross-route hash resolution. Full navbar starts
at 1280px; smaller widths retain the accessible drawer and close it after link navigation.
The Campus Resources heading/description and official destinations remain unchanged.
No Campus Resources API, auth dependency or database state is introduced.

Responsive verification records cover desktop/tablet/mobile widths and horizontal overflow;
they are scoped to each task, not evidence that every route passes every viewport. UI tests
check semantic behavior and focus/role contracts. Preserve reduced motion, image decoding,
keyboard focus and EN/DE strings when extending these sections.

History and acceptance: [About task](../../implementation/tasks/FE-LANDING-ABOUT-001.md),
[CTA task](../../implementation/tasks/FE-LANDING-CTA-001.md),
[slideshow task](../../implementation/tasks/FE-LANDING-BG-002.md),
[User Events task](../../implementation/tasks/FE-USER-EVENTS-001.md).
