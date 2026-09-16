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

## Source entry points

| Path                             | Responsibility                                                       |
| -------------------------------- | -------------------------------------------------------------------- |
| `src/main.tsx`                   | React mount, router, query provider, and localization initialization |
| `src/App.tsx`                    | Public, student, and administrator route definitions                 |
| `src/components/layout/`         | Navbar, footer, language toggle, and layout wrappers                 |
| `src/components/landing/`        | Landing sections, carousel, and demo dialog                          |
| `src/pages/public/`              | Landing and authentication forms                                     |
| `src/features/events/`           | Event schema, API/mock repositories, and query hook                  |
| `src/lib/api.ts`                 | Public GET client using `VITE_API_URL`                               |
| `src/i18n.ts` and `src/locales/` | English/German localization                                          |
| `src/test/setup.ts`              | Test environment setup; test files are colocated with source         |

The `@/` alias resolves to `src/`. Tests run through `vitest.config.ts`; the build uses `vite.config.ts`. ESLint and Prettier are the configured lint/format tools.

See [CONTRIBUTING.md](../../CONTRIBUTING.md) before submitting changes.
