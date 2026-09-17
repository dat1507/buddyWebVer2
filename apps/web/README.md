# VGU Buddy frontend

React and TypeScript single-page application for the VGU Buddy Program rebuild.

See the [root README](../../README.md) for product context, screenshots, architecture, configuration, and implementation status. The current package contains the public website, UI-only authentication pages, and placeholder student/admin routes.

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

Production builds do not use the event fixtures, even with `VITE_EVENT_SLIDER_USE_MOCKS=true`. Without a working event API configured at build time, the carousel displays its error state in preview. Authentication remains UI-only in both modes.

## In-memory session store (AUTH-004)

`useAuthStore` in `src/stores/auth-store.ts` is a typed Zustand 5.0.15 singleton for this browser SPA.
It starts with `status: 'unknown'`, `user: null`, `role: null`. It is not yet connected to login,
registration, API bootstrap or route guards: AUTH-021 owns the credentialed client, `/api/auth/me`
bootstrap, single-flight refresh and logout coordination. AUTH-005/AUTH-006 own guards.

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
of stale local/sessionStorage data, until AUTH-021 resolves `/api/auth/me`. Keep JWTs exclusively in
backend-set HttpOnly cookies and the readable CSRF value in AUTH-021's client memory, not this store.
Client role/state is presentation only and cannot authorize backend access. The singleton is for
the current client-only SPA; any future SSR implementation needs per-request state isolation.

`clearSession()` only clears this in-memory view: it does **not** call backend logout, expire actual
cookies, clear TanStack Query caches, prevent late async responses or invalidate a copied access
JWT. AUTH-024's combined frontend/cache acceptance remains pending AUTH-021. No end-to-end/browser
login/logout or production deployment is claimed by AUTH-004; no new environment configuration.

Focused checks (real Zustand + React selector hook, not a mocked store):

```sh
npm test -- src/features/auth/session-user.test.ts src/stores/auth-store.test.ts
```

Security/reload checks include payload projection, strict roles/booleans, immutable copied users,
fail-closed invalid data, no storage/cookie/network calls, and fresh-module `unknown` with stale
storage. Implementation references: [Zustand typed stores/reset](https://github.com/pmndrs/zustand/blob/main/docs/learn/guides/beginner-typescript.md)
and [Zod object field projection](https://zod.dev/api#objects).

## Source entry points

| Path                                | Responsibility                                                       |
| ----------------------------------- | -------------------------------------------------------------------- |
| `src/main.tsx`                      | React mount, router, query provider, and localization initialization |
| `src/App.tsx`                       | Public, student, and administrator route definitions                 |
| `src/components/layout/`            | Navbar, footer, language toggle, and layout wrappers                 |
| `src/components/landing/`           | Landing sections, carousel, and demo dialog                          |
| `src/pages/public/`                 | Landing and authentication forms                                     |
| `src/features/events/`              | Event schema, API/mock repositories, and query hook                  |
| `src/features/auth/session-user.ts` | Sanitized session User validation and readonly DTO types             |
| `src/stores/auth-store.ts`          | Non-persisted status/user/role state and atomic actions              |
| `src/lib/api.ts`                    | Public GET client using `VITE_API_URL`                               |
| `src/i18n.ts` and `src/locales/`    | English/German localization                                          |
| `src/test/setup.ts`                 | Test environment setup; test files are colocated with source         |

The `@/` alias resolves to `src/`. Tests run through `vitest.config.ts`; the build uses `vite.config.ts`. ESLint and Prettier are the configured lint/format tools.

See [CONTRIBUTING.md](../../CONTRIBUTING.md) before submitting changes.
