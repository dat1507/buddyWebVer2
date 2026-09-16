# Repository presentation audit

Audit date: **2026-09-11**. Source baseline: **`fced9f3`**, repository **`dat1507/buddyWebVer2`**.

## Scope and identity

The requested repository was found at `C:/Users/phuoc/Downloads/buddyWebVer2`, with an origin matching the supplied GitHub screenshot. The initially selected workspace, `VGU_Buddy_Website`, is the separate legacy `dat1507/buddy_website` repository. No legacy application files are part of this documentation change.

The audit inspected the tracked file inventory, package and lockfile configuration, public pages, layout and routing code, event data flow, localization, UI components, tests, environment example, assets, and relevant implementation-plan milestones. Generated `dist` and installed dependencies were treated as local build/runtime artifacts, not additional implemented product features. The working tree was clean before this task.

## Findings and source evidence

| Area                  | Verified state                                                                                                               | Evidence                                                                                                                                                                         |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Root presentation     | No root README at the audited baseline; package README was generic React/Vite/Oxlint template copy                           | Root tree and previous `apps/web/README.md`                                                                                                                                      |
| Package manager       | One npm package in `apps/web`, with a committed npm lockfile; no root package/workspace configuration                        | [Manifest](../apps/web/package.json), [lockfile](../apps/web/package-lock.json)                                                                                                  |
| Framework             | React 19, React Router 8, TypeScript 6, Vite 8; strict mode enabled                                                          | [Manifest](../apps/web/package.json), [TypeScript config](../apps/web/tsconfig.app.json)                                                                                         |
| Styling               | Tailwind CSS 3, local UI primitives, Radix Slot and CVA; shadcn configuration exists                                         | [UI configuration](../apps/web/components.json), [UI directory](../apps/web/src/components/ui)                                                                                   |
| Public site           | Six assembled landing sections with shared navbar/footer and responsive classes                                              | [Landing](../apps/web/src/pages/public/landing-page.tsx), [public layout](../apps/web/src/components/layout/public-layout.tsx)                                                   |
| Student login         | Required email/password, native email validity, error focus; valid submit sets backend notice only                           | [Login page](../apps/web/src/pages/public/user-login-page.tsx)                                                                                                                   |
| Student registration  | Email/password and explicit consent validation; no API call or account creation                                              | [Registration page](../apps/web/src/pages/public/user-registration-page.tsx)                                                                                                     |
| Admin entry           | Separate UI at `/adminLogin`, not exposed in public navigation; no authentication or provisioning code                       | [Admin login](../apps/web/src/pages/public/admin-login-page.tsx), [navbar tests](../apps/web/src/components/layout/navbar.test.tsx)                                              |
| User/admin separation | Distinct route groups and layout wrappers; all nested product pages are placeholders and are unguarded                       | [Routes](../apps/web/src/App.tsx), [placeholder](../apps/web/src/pages/route-placeholder.tsx)                                                                                    |
| Events                | Working carousel frontend, development fixtures, public GET adapter, Zod validation, query refetching                        | [Events feature](../apps/web/src/features/events), [carousel](../apps/web/src/components/landing/events-slider.tsx)                                                              |
| Localization          | EN/DE resource files, browser detection, language preference stored as `vgu-language`                                        | [i18n](../apps/web/src/i18n.ts), [locales](../apps/web/src/locales)                                                                                                              |
| Forms/state           | React refs/state plus native input validity; Zod is used for event payloads                                                  | Auth page sources and [schema](../apps/web/src/features/events/event-slider.ts)                                                                                                  |
| Backend/database      | No backend application, server endpoint implementation, ORM models, migration scripts, or database setup in the tracked tree | Tracked tree; future contracts in [implementation plan](../implementation_plan_vgu_buddy.md)                                                                                     |
| Environment           | API URL and development fixture toggle are consumed; GA ID is an unused example value                                        | [.env.example](../apps/web/.env.example), [API client](../apps/web/src/lib/api.ts), [provider](../apps/web/src/features/events/repositories/event-slider-repository-provider.ts) |
| Deployment/CI         | No checked-in hosting configuration, Docker setup, or `.github/workflows`; no current rebuild live URL verified              | Tracked tree; deployment sections are in the plan only                                                                                                                           |
| Tests/quality         | Vitest/jsdom, Testing Library, ESLint, Prettier, and strict TypeScript are configured                                        | [Test config](../apps/web/vitest.config.ts), [lint config](../apps/web/eslint.config.js), [scripts](../apps/web/package.json)                                                    |
| Branding/media        | Existing Buddy logo, custom favicon, community photo, bundled demo video/poster, Survival Book, and mock event posters       | [Assets](../apps/web/src/assets), [public assets](../apps/web/public)                                                                                                            |
| Screenshots           | No dedicated current-app screenshots found at baseline; new captures are from the running local app                          | [Capture notes](images/README.md)                                                                                                                                                |
| License               | No project license file at baseline                                                                                          | Root inventory and package manifest                                                                                                                                              |

The remaining feature directories (`admin`, `assistant`, `auth`, `campus`, `matching`, `profile`) and `stores` are scaffolding containing `.gitkeep` files. The `react.svg`, `vite.svg`, and other existing assets were not removed as part of this presentation task.

## Route inventory

Source: [src/App.tsx](../apps/web/src/App.tsx).

| Route                                                                                                                                                                                               | Actual behavior                         |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| `/`                                                                                                                                                                                                 | Implemented public landing page         |
| `/login`                                                                                                                                                                                            | UI-only student login                   |
| `/register`                                                                                                                                                                                         | UI-only student registration            |
| `/adminLogin`                                                                                                                                                                                       | UI-only administrator login, direct URL |
| `/user`                                                                                                                                                                                             | Redirects to `/user/dashboard`          |
| `/user/dashboard`, `/user/profile`, `/user/matching`, `/user/buddy`, `/user/assistant`, `/user/campus`, `/user/events`, `/user/settings`                                                            | Placeholder pages                       |
| `/admin`                                                                                                                                                                                            | Redirects to `/admin/dashboard`         |
| `/admin/dashboard`, `/admin/users`, `/admin/matching`, `/admin/events`, `/admin/announcements`, `/admin/knowledge-base`, `/admin/campus`, `/admin/analytics`, `/admin/audit-log`, `/admin/settings` | Placeholder pages                       |
| Other unmatched paths                                                                                                                                                                               | Not-found page                          |

There are no protected routes, live role redirects, server-enforced RBAC, or working session lifecycle. The “restricted area” and “provisioned credentials” text on the admin form describes intended use, not implemented security.

## Event data boundary

The repository provider selects development fixtures only when `import.meta.env.DEV` is true and `VITE_EVENT_SLIDER_USE_MOCKS` is not the exact string `false`. Production uses the API adapter even if the variable is `true`.

The adapter requests `<VITE_API_URL>/event-sliders?locale=en|de`, validates a JSON array, and maps API snake_case fields to the frontend model. The query refetches every 60 seconds; global defaults set a 30-second stale time, one retry, and window-focus refetching. This is a frontend contract, not evidence that an endpoint exists.

No admin slider CRUD, publishing service, storage upload integration, or event registration exists here yet. The carousel's posters are fixtures and do not establish a live upcoming-events schedule.

## Differences from the implementation plan

- Part 1 audits the **legacy HTML/JavaScript website**, not the current React rebuild. Its chatbot, merchandise page, calendar, and Vercel proxy must not be presented as existing features of this repository.
- The proposed stack mentions React 18 and React Router 6; the actual manifest uses React 19 and React Router 8. Documentation uses the manifest.
- Zustand and React Hook Form are proposed but are absent from the current dependencies. Do not describe the forms as using them.
- `AUTH-ARCH-001` is complete as a **design decision**. HttpOnly JWT cookies, CSRF protection, session bootstrap, role guards, and refresh/logout flows remain implementation work.
- Part 24 identifies `BE-001` as the next backend foundation task. No backend work is claimed as underway merely because it is listed next.
- Features such as matching, RAG, campus maps, notifications, gamification, analytics, and admin management are planned. Their route labels or promotional text do not establish functionality.
- The landing benefit cards are intentionally informational and have no navigation. They do not implement shopping, bookings, library access, or dormitory services.
- Hosting plans, free-tier estimates, usage claims in marketing copy, coverage targets, and proposed CI are not verified operational facts. They were not promoted to README badges or statistics.

## Local verification

Verified on 2026-09-11 using Node.js **24.11.0** and the already-installed package dependencies at baseline `fced9f3`:

| Check                          | Result                                                                                               |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Prettier check                 | Passed                                                                                               |
| ESLint                         | Passed                                                                                               |
| TypeScript project build/check | Passed                                                                                               |
| Vitest                         | **14 test files, 80 tests passed**                                                                   |
| Vite production build          | Passed; existing advisory about a minified JavaScript chunk exceeding 500 kB                         |
| Browser inspection             | Landing, login, registration, and admin login render; captured landing and login surfaces in English |

The default `npm` command on the audit machine pointed to a missing roaming npm CLI. Checks were run using Node and the project's installed CLI entry points for Prettier, ESLint, Vitest, TypeScript, and Vite, matching the package scripts. A clean `npm ci` installation was **not** rerun. The README gives the normal npm workflow for a working Node/npm installation.

These are local results, not CI results or a coverage measurement. Browser inspection was not a full accessibility audit, responsive-device matrix, or backend integration test.

## Presentation changes

- Add a root README with consistent VGU Buddy branding, five factual stack/status badges, current architecture, genuine UI previews, local setup, and an explicit roadmap.
- Replace template package documentation with a concise frontend guide.
- Add a contribution guide, this source-backed audit, screenshot maintenance notes, and prepared GitHub About fields.
- Reuse the existing logo without copying or replacing it.
- Keep application runtime code, dependencies, the implementation plan, and project licensing unchanged.

GitHub About changes require an authenticated repository owner session. The connected browser was logged out during this audit, so [prepared About fields](github-presentation.md) are provided separately. Local documentation changes still need to be committed and pushed to appear on GitHub.
