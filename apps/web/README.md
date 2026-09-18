# VGU Buddy frontend

React and TypeScript single-page application for the VGU Buddy Program rebuild.

See the [root README](../../README.md) for product context, screenshots, architecture, configuration, and implementation status. The current package contains the public website, API-connected authentication forms, and placeholder student/admin routes.

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
client, `/api/auth/me` bootstrap, login and logout. AUTH-005/AUTH-006 still own route guards.

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
backend endpoint and install the actual returned User/role. They currently display successful login
on the same page: role checks/redirects belong to AUTH-022/023, after AUTH-005/006.

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

## Source entry points

| Path                                  | Responsibility                                                       |
| ------------------------------------- | -------------------------------------------------------------------- |
| `src/main.tsx`                        | React mount, router, query provider, and localization initialization |
| `src/App.tsx`                         | Public, student, and administrator route definitions                 |
| `src/components/layout/`              | Navbar, footer, language toggle, and layout wrappers                 |
| `src/components/landing/`             | Landing sections, carousel, and demo dialog                          |
| `src/pages/public/`                   | Landing and authentication forms                                     |
| `src/features/events/`                | Event schema, API/mock repositories, and query hook                  |
| `src/features/auth/session-user.ts`   | Sanitized session User validation and readonly DTO types             |
| `src/stores/auth-store.ts`            | Non-persisted status/user/role state and atomic actions              |
| `src/features/auth/session-client.ts` | CSRF, bootstrap, refresh, login/logout and account coordination      |
| `src/features/auth/private-cache.ts`  | Targeted private-query cancellation/removal                          |
| `src/lib/api.ts`                      | Credentialed JSON/CSRF client using `VITE_API_URL`                   |
| `src/i18n.ts` and `src/locales/`      | English/German localization                                          |
| `src/test/setup.ts`                   | Test environment setup; test files are colocated with source         |

The `@/` alias resolves to `src/`. Tests run through `vitest.config.ts`; the build uses `vite.config.ts`. ESLint and Prettier are the configured lint/format tools.

See [CONTRIBUTING.md](../../CONTRIBUTING.md) before submitting changes.
