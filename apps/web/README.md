# VGU Buddy frontend

React and TypeScript single-page application for the VGU Buddy Program rebuild.

See the [root README](../../README.md) for product context, screenshots, architecture, configuration, and implementation status. The current package contains the public website, API-connected authentication forms, a responsive student layout shell, and placeholder student/admin pages.

## Run locally

Use Node.js 22.12+ and npm. From this directory (`apps/web`):

```sh
npm ci
npm run dev
```

The landing page uses development event fixtures by default. No backend or environment file is required for this mode. For custom settings, copy `.env.example` to `.env.local`; see the [environment reference](../../README.md#environment-variables).

## Commands

| Command                                   | Purpose                                        |
| ----------------------------------------- | ---------------------------------------------- |
| `npm run dev`                             | Start the Vite development server              |
| `npm run typecheck`                       | Run TypeScript project checks                  |
| `npm run lint` / `npm run lint:fix`       | Check ESLint rules / apply supported fixes     |
| `npm run format:check` / `npm run format` | Check formatting / format package files        |
| `npm test`                                | Run Vitest once with jsdom and Testing Library |
| `npm run build`                           | Type-check and generate `dist`                 |
| `npm run preview`                         | Serve the existing production build locally    |

Production builds do not use the event fixtures, even with `VITE_EVENT_SLIDER_USE_MOCKS=true`. Without a working event API configured at build time, the carousel displays its error state in preview. Authentication uses the configured `VITE_API_URL` in both modes; a missing/unavailable API displays safe feedback and permits retry.

## In-memory session store (AUTH-004)

`useAuthStore` in `src/stores/auth-store.ts` is a typed Zustand 5.0.15 singleton for this browser SPA.
It starts with `status: 'unknown'`, `user: null`, `role: null`. AUTH-021 connects it to the credentialed
client, `/api/auth/me` bootstrap, login and logout. AUTH-005 supplies authentication route guards;
AUTH-006 adds exact-role guards for private User/Admin descendants.

| Action                      | Result                                                                      |
| --------------------------- | --------------------------------------------------------------------------- |
| `startLoading()`            | `loading`, with user/role cleared                                           |
| `setAuthenticated(payload)` | Validated `authenticated` user and its derived role, updated atomically     |
| `clearSession()`            | `unauthenticated`, with user/role cleared; safe to repeat                   |
| `resetSession()`            | Neutral `unknown`, with user/role cleared; not a confirmed logged-out state |

`setAuthenticated` accepts only the backend sanitized User shape: UUID `id`, non-empty string
`email`, exact `USER`/`ADMIN` `role`, and strict boolean `email_verified`. This is minimal session
wire validation, not a replacement for backend registration/email validation. Unknown fields are
discarded; password/hash, JWTs, CSRF, profile and private data are never copied into store state.
The resulting four scalar fields are copied and frozen. Invalid data clears any previous account
and throws generic `SessionUserValidationError`, without retaining payloads/validation issues.
Use the actions as the supported mutation API; do not merge untrusted data with native `setState`.

There is no persist/devtools middleware, Web Storage/IndexedDB access, cookie read/write or network
request. The store itself does not restore a session: a new page/module starts `unknown`, regardless
of stale local/sessionStorage data, until the session client resolves `/api/auth/me`. Keep JWTs exclusively in
backend-set HttpOnly cookies and the readable CSRF value in AUTH-021's client memory, not this store.
Client role/state is presentation only and cannot authorize backend access. The singleton is for
the current client-only SPA; any future SSR implementation needs per-request state isolation.

`clearSession()` only clears this in-memory view: it does **not** call backend logout, expire actual
cookies, clear TanStack Query caches, prevent late async responses or invalidate a copied access
JWT. Use `sessionClient.logout()` for the coordinated backend/cache operation. AUTH-021 verifies
the integrated flow; AUTH-004 alone does not claim backend/browser logout or production deployment.

Focused checks (real Zustand + React selector hook, not a mocked store):

```sh
npm test -- src/features/auth/session-user.test.ts src/stores/auth-store.test.ts
```

Security/reload checks include payload projection, strict roles/booleans, immutable copied users,
fail-closed invalid data, no storage/cookie/network calls, and fresh-module `unknown` with stale
storage. Implementation references: [Zustand typed stores/reset](https://github.com/pmndrs/zustand/blob/main/docs/learn/guides/beginner-typescript.md)
and [Zod object field projection](https://zod.dev/api#objects).

## Session client and forms (AUTH-021)

`src/lib/api.ts` sends `credentials: 'include'`, JSON bodies, and `X-CSRF-Token` for unsafe methods.
Auth requests bypass caches. Failures retain only a sanitized status/code and optional Retry-After;
requests have cancellation and a 15-second timeout. JWTs remain exclusively in backend-set HttpOnly
cookies. The readable CSRF response stays in the session client's closure, never in storage/store.

On mount, `SessionBootstrap` deduplicates bootstrap, including React StrictMode's effect replay.
It calls `GET /auth/csrf/session` with browser cookies, then `/auth/me`. If access has expired, it
refreshes once with session CSRF and retries `/me` once. Anonymous/expired sessions clear identity;
configuration/network/server failures finish pending and expose a manual retry. A reload repeats
this verification from fresh memory rather than trusting a persisted client identity.

Registration acquires pre-auth CSRF and submits only email/password/consent. Validation enforces
15 Unicode characters and the backend's 72 UTF-8-byte maximum. Only a verified backend registration
response navigates to `/login`; registration never authenticates. Both login pages submit the same
backend endpoint. AUTH-022 routes `/login` by actual role; AUTH-023 requires validated ADMIN before
installing identity at `/adminLogin`, otherwise revokes the newly issued USER session and denies publicly.

Use `sessionClient.authenticatedJson()` for future private API requests. Concurrent 401s share one
refresh and each request retries once; a delayed 401 cannot trigger a second completed rotation.
Session CSRF rejection permits one recovery/retry. Auth cookie operations serialize within this
tab; logout/account-switch intent immediately hides the prior account and cancels private queries.
Older bootstrap/refresh/private responses cannot restore that identity or return its data. Login
revokes an existing live family before submitting new credentials. Logout reports success only
after the backend 204; failure remains locally cleared and exposes retry.

Private query keys must begin with `private`, `profile`, `profiles`, `match`, `matches`, `matching`,
or `private-media`, or carry `meta: { private: true }`. Prefer `['private', userId, ...]` for new
features. Cancellation plus removal prevents late private data repopulation while public
`event-sliders` queries remain cached. No global QueryClient wipe is used.

Forms prevent duplicate submit, disable pending controls, expose accessible EN/DE feedback, and
suppress completion navigation after unmount. They do not log passwords, backend bodies or tokens.
The controller coordinates one tab; it does not claim cross-tab locking or immediate access JWT
denylisting. Backend's existing copied-access TTL and production Redis/TLS release gate remain.

Focused checks:

```sh
npm test -- src/lib/api.test.ts src/features/auth/session-client.test.ts src/features/auth/auth-integration.test.tsx
```

Verification (2026-09-18): full frontend **175 PASS**, formatting/lint/typecheck/build and production
dependency audit PASS. Real local browser + isolated PostgreSQL registration/login/reload/logout
PASS; backend live tests also cover expired-access refresh and persisted USER/ADMIN roles. Public
slider transport/cache regression and EN/DE rendering PASS. No production deployment is claimed.

## Protected routes (AUTH-005)

`src/features/auth/protected-route.tsx` is a reusable React Router outlet guard backed by the
actual AUTH-004 status selector. The AUTH-ARCH-001 contract requires neutral pending while status
is `unknown` or `loading`: private children/layouts never mount and the requested URL stays intact.
Confirmed `unauthenticated` state redirects with history replacement to a fixed internal login
path: `/user` descendants use `/login`, `/admin` descendants use `/adminLogin`. Router state keeps
only the requested pathname/search/hash for later login-flow work; the guard does not follow it.
Public landing, login, registration, direct Admin login and 404 routes remain outside the guard.

Validated `authenticated` state renders the nested outlet and existing dashboard index navigation.
Logout immediately unmounts private content; account re-verification returns to neutral pending.
The guard never fetches, inspects cookies, reads storage or restores an identity itself. AUTH-021
alone owns bootstrap/refresh. A focused integration check exposed early identity installation
after bootstrap refresh; bootstrap now validates that response without installing identity until
the final `/me` succeeds. Normal private-request refresh still installs the verified updated User.

ProtectedRoute handles authentication presentation only; App now uses AUTH-006 RoleGuard to
separate authenticated identities by role. AUTH-022 completes User login routing; AUTH-023 completes
Admin login redirects/denial as documented below.
Backend `require_auth`/`require_role` remain authoritative. Existing placeholder pages stay
placeholders, not delivered profile/admin features. No API/cookie/CSRF/dependency/env change.

```sh
npm test -- src/features/auth/protected-route.test.tsx src/features/auth/protected-route-integration.test.tsx
```

Verification (2026-09-18): **31 focused PASS; full frontend 206 PASS**; Prettier, ESLint, strict
TypeScript, production build and production dependency audit PASS. Full backend regression **384 PASS / 10 existing Redis live
SKIP**, including the isolated PostgreSQL live suite. Real local browser + backend/database cookies
verify anonymous User/Admin redirects, authenticated deep-link reload without login redirect,
and logout followed by denied re-entry. EN/DE checks PASS; browser error console empty. Existing
chunk-size advisory, access JWT residual TTL and production AUTH-020 operator gate remain.

## Role guards (AUTH-006)

`src/features/auth/role-guard.tsx` accepts a typed `requiredRole` (`USER` or `ADMIN`) and fixed
internal `loginPath`. Unknown/loading/anonymous sessions delegate to ProtectedRoute, reusing
neutral accessible EN/DE pending and verified anonymous login redirects. App requires USER for
all declared `/user` descendants, ADMIN for all declared `/admin` descendants, including indexes.
There is no ADMIN override for User-only pages. A verified wrong role replaces history with public
`/` before the private layout/outlet mounts; query/hash/router state cannot choose that destination.
Denial preserves the valid session and never initiates logout or cookie/network/storage work.

Reactive store selectors remove incompatible content immediately when role changes, session clears
or account verification restarts. AUTH-021 waits for final `/me` after bootstrap refresh; a refresh
payload alone cannot expose private UI. Its existing verified role-change handling clears private
queries before installing identity and retains public event sliders. The guard adds no API calls,
credentials, persistence, dependencies or backend authorization. Backend verifies cookies/current
database roles independently; this guard is a UX layer. AUTH-022 now supplies User login routing;
AUTH-023 supplies wrong-role Admin-login logout/redirect; business/layout pages remain placeholders.

```sh
npm test -- src/features/auth/role-guard.test.tsx src/features/auth/role-guard-integration.test.tsx
```

Verification (2026-09-18): **50 focused PASS; full frontend 256 PASS**; Prettier, ESLint, strict
TypeScript, production build and production npm audit (zero vulnerabilities) PASS. Full backend
**384 PASS / 10 existing opt-in Redis live SKIP** includes three isolated PostgreSQL cases; Ruff,
strict mypy (57 files), pip check PASS. Strict pip-audit of all 77 pinned external installed
distributions PASS; local editable source `vgu-buddy-api` is reviewed as repository code, not a
PyPI distribution. Audit input and acceptance lab are Git-ignored; no dependency/env file changed.
Real local browser + backend/database cookies verify both roles, matching deep-link reload,
cross-role denial/session retention, index navigation, EN/DE, logout and denied re-entry. Error
console empty. Git diff/credential-signature checks PASS. Existing chunk advisory and production
AUTH-020 operator gate remain. AUTH-006 preceded the User login flow documented below.

## User login flow (AUTH-022)

`UserLoginPage` observes the verified AUTH-004 status and exact sanitized role. Successful login or
an already verified/recovered session visiting `/login` replaces history with `/user/dashboard`
for USER, `/admin/dashboard` for ADMIN. Unknown/loading/anonymous identity does not trigger success
routing; AUTH-021's final `/me` controls reload recovery, including the bounded refresh path.
Destinations are fixed internal constants. Query/hash/router state (`state.from`) and stale Web
Storage cannot choose a role or URL; no return-to URL contract or `/adminLogin` public link is added.

Validation/focus, form `aria-busy`, disabled pending controls, duplicate-submit prevention, safe
EN/DE errors and manual retry reuse AUTH-021. Successful login clears the submitted password input
even if routing has detached it. Success presentation is now the verified private destination.
Completion after leaving the form does not navigate the public page; logout/superseding intent
suppresses late identity through the existing session-client epoch and serialized cookie queue.
Signout followed by a new User/Admin login preserves public sliders and removes private cache.
The guard still verifies role before any private layout renders; backend authorization is independent.

The existing dashboard routes/pages are scaffolding. Readiness-aware onboarding routing is FE-038
after BE-016/FE-027; it is not fabricated here. `/adminLogin` role denial/logout/redirect is AUTH-023.
No API/client/CSRF/store/backend/env/schema/dependency contract changes or production deployment.

```sh
npm test -- src/features/auth/user-login-flow.test.tsx src/pages/public/user-login-page.test.tsx src/features/auth/auth-integration.test.tsx
```

Verification (2026-09-18): **31 dedicated AUTH-022 PASS; full frontend 287 PASS**. Prettier, ESLint,
strict TypeScript, production build and production npm audit PASS (zero vulnerabilities). Full
backend regression **384 PASS / 10 existing opt-in Redis live SKIP**, including three isolated
PostgreSQL live cases; Ruff, strict mypy (57 files), pip check and Alembic single head PASS.
Strict pip-audit of the pinned runtime `requirements.lock` PASS (no known vulnerabilities).
Real local browser + isolated PostgreSQL/cookies verifies USER login in DE, ADMIN via `/login` in EN,
role dashboards, recovered `/login` sessions, ignored redirect queries, reload, logout/denied
re-entry; browser error console empty. Git diff/credential-signature review PASS; lab/build/env
outputs excluded. Existing chunk advisory and AUTH-020 production operator gate remain.
Next development task: AUTH-023; not started by AUTH-022.

## Admin login flow (AUTH-023)

`AdminLoginPage` calls the same backend endpoint through `sessionClient.login(credentials,
{ requiredRole: 'ADMIN' })`. This option is local policy and is never sent in the request body.
Only a validated sanitized ADMIN is installed; it replaces history with `/admin/dashboard`.
Caller query/hash/router state/stale storage cannot choose a role or redirect destination.

A successful USER response never enters authenticated client state, even while revocation is
pending. The client uses that response's session-bound CSRF to logout inside the serialized login
operation, including one bounded 403 recovery/retry. After cleanup, the form clears its password
and replaces history with `/` and a fixed accessible EN/DE denial notice. Landing renders only
the whitelisted notice code, never arbitrary router-state text. Failed logout also redirects
with denial, keeps local identity cleared and exposes the existing safe logout error/retry;
server revocation is not claimed until a successful backend response. Retry never resubmits credentials.

Previously verified/recovered ADMIN entering this public page routes to the dashboard; an
existing USER is denied publicly while its established valid session is retained. This differs
from the plan's explicit cleanup of a newly issued wrong-role login session. Unknown/loading
wait for final `/me`; errors stay on the form with safe manual retry. Duplicate submissions,
unmount and superseding login/logout remain protected by existing hooks/queue/epoch checks.
Private queries clear while public event sliders remain. No backend/cookie/storage/schema/env/
dependency change, Admin discovery link, self-registration or production deployment is added.

```sh
npm test -- src/features/auth/admin-login-flow.test.tsx src/pages/public/admin-login-page.test.tsx src/features/auth/auth-integration.test.tsx
```

Verification (2026-09-18): **34 dedicated AUTH-023 PASS; full frontend 321 PASS**; format/ESLint/
strict TypeScript/build PASS, production npm audit zero vulnerabilities. Backend **384 PASS /
10 opt-in Redis live SKIP**, including three isolated PostgreSQL cases; Ruff/strict mypy (57 files)/
pip check/Alembic single head and strict runtime lockfile pip-audit PASS. Actual local browser/API/
PostgreSQL verifies ADMIN login and recovered Admin entry, USER denial/logout in EN/DE, anonymous
private-route re-entry after cleanup, valid User login and existing USER denial/session retention.
Browser error console empty; Git diff/credential review PASS. Existing chunk-size advisory,
copied-access TTL and AUTH-020 production operator gate remain. Private pages are scaffolding;
readiness/onboarding remains FE-038. Next development task: FE-021; not started by AUTH-023.

## Student layout shell (FE-021)

`src/components/layout/user-layout.tsx` supplies the USER sidebar and one main content landmark
around React Router's `Outlet`. Existing App composition keeps it inside `ProtectedRoute` and
the exact USER `RoleGuard`: unknown/loading, anonymous and ADMIN identities cannot mount it.
The shell has no API, session, persistence or business-navigation behavior.

The shared Card, Typography, brand asset and LanguageToggle reuse the current design system.
Below the `lg` breakpoint, sidebar and content stack; desktop uses a 16rem sidebar and a flexible
content column within `max-w-7xl`. Both regions permit content to shrink. The existing body owns
the viewport minimum height, avoiding an additional viewport-height shell below session controls.
EN/DE sidebar/content labels and a focus-visible skip link update with localization. The link
targets the uniquely identified, programmatically focusable main. User placeholders render a div
inside that main; Public/Admin placeholders retain their existing main landmark.

```sh
npm test -- src/components/layout/user-layout.test.tsx src/components/layout/user-layout-integration.test.tsx
```

Verification (2026-09-18): **12 dedicated FE-021 PASS; full frontend 333 PASS**. Format, ESLint,
TypeScript, production build and production npm audit PASS. Backend regression **384 PASS /
10 existing opt-in Redis live SKIP**, Ruff/mypy/pip check/Alembic/package build, strict runtime
lockfile pip-audit and Compose validation PASS. Actual local browser/API/PostgreSQL verifies
USER login, deep-link reload, desktop/320px layout without horizontal overflow, EN/DE labels,
keyboard skip-link focus, logout and denied re-entry. Browser error console empty.

Next development task: **FE-022 — User Sidebar navigation**; not implemented here. Dashboard,
profile/onboarding and Admin business pages remain scaffolding. Existing bundle-size advisory,
copied-access TTL and AUTH-020 production Redis/TLS/ingress operator gate remain.

## Student sidebar navigation (FE-022)

`UserSidebarNavigation` adds a named navigation landmark and seven localized items: Dashboard,
My Profile, Edit Profile, Buddy Matching, My Buddy, Events and Settings. Calendar/Notifications
appear only after delivery; assistant/campus/Admin links are outside this sidebar's scope.

`src/routes/user-routes.ts` is the shared route registry. A `placeholder` route renders the existing
scaffolding and cannot produce an actionable sidebar link. A delivered `page` must supply its actual
component; routing and navigation use that same descriptor. All current student pages remain
placeholders. Their sidebar entries are `aria-disabled` spans without href or tab stops, with a
localized explanation and status. Edit Profile has no existing route, so it has no destination URL.

Current locations use `aria-current="page"`, including requested scaffold routes. Delivered-page
inputs render native NavLinks with focus-visible styles, exact profile/dashboard matching and
nested matching/buddy/events/settings support. Search/hash do not select a different destination.
Unit fixtures exercise this released-page branch without claiming business features are delivered.

Navigation stacks at narrow widths, uses two columns at `sm` and returns to one desktop sidebar
column at `lg`. Labels/status wrap independently. Removing the body's fixed 320px minimum width
allows a 320px viewport with a vertical scrollbar to fit its actual available content width.
Existing FE-021 skip-link/main behavior, language toggle, guards and session/client flow remain.

```sh
npm test -- src/components/layout/user-sidebar-navigation.test.tsx src/components/layout/user-sidebar-navigation-integration.test.tsx
```

Verification (2026-09-18): **21 dedicated FE-022 PASS; FE-021 regression 12 PASS; full frontend
354 PASS**. Format/lint/typecheck/build and production dependency audit PASS. Backend full suite:
381 PASS / 13 opt-in live SKIP; three PostgreSQL opt-in cases additionally PASS, leaving ten Redis
live cases unconfigured. Ruff/mypy/pip check/Alembic/package build, strict lockfile pip-audit and
Compose validation PASS. Actual local browser/API/PostgreSQL checks verify deep-link reload,
desktop/320px layout, EN/DE, keyboard skip/focus without unavailable tab stops, logout and denied
re-entry. Private/public mobile content has no horizontal overflow; browser error console empty.

Direct-to-main workflow applies from FE-022 onward. Next task: **ADMIN-001 — Create AdminLayout
component (sidebar + content)**; not implemented here. FE-023 still awaits profile/readiness/
onboarding dependencies. Existing bundle-size advisory and AUTH-020 production operator gate remain.

## Source entry points

| Path                                    | Responsibility                                                       |
| --------------------------------------- | -------------------------------------------------------------------- |
| `src/main.tsx`                          | React mount, router, query provider, and localization initialization |
| `src/App.tsx`                           | Public, student, and administrator route definitions                 |
| `src/routes/user-routes.ts`             | Student route components/placeholders and shared delivery metadata   |
| `src/routes/user-navigation.ts`         | Scoped sidebar items and availability derived from route delivery    |
| `src/components/layout/`                | Navbar, footer, language toggle, and layout wrappers                 |
| `src/components/landing/`               | Landing sections, carousel, and demo dialog                          |
| `src/pages/public/`                     | Landing and authentication forms                                     |
| `src/features/events/`                  | Event schema, API/mock repositories, and query hook                  |
| `src/features/auth/session-user.ts`     | Sanitized session User validation and readonly DTO types             |
| `src/stores/auth-store.ts`              | Non-persisted status/user/role state and atomic actions              |
| `src/features/auth/session-client.ts`   | CSRF, bootstrap, refresh, login/logout and account coordination      |
| `src/features/auth/private-cache.ts`    | Targeted private-query cancellation/removal                          |
| `src/features/auth/protected-route.tsx` | Pending/authenticated/anonymous outlet behavior                      |
| `src/features/auth/role-guard.tsx`      | Exact-role outlet gating and fixed public wrong-role redirect        |
| `src/lib/api.ts`                        | Credentialed JSON/CSRF client using `VITE_API_URL`                   |
| `src/i18n.ts` and `src/locales/`        | English/German localization                                          |
| `src/test/setup.ts`                     | Test environment setup; test files are colocated with source         |

The `@/` alias resolves to `src/`. Tests run through `vitest.config.ts`; the build uses `vite.config.ts`. ESLint and Prettier are the configured lint/format tools.

See [CONTRIBUTING.md](../../CONTRIBUTING.md) before submitting changes.
