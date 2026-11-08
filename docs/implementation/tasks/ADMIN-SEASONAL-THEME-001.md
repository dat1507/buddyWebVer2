# ADMIN-SEASONAL-THEME-001 — Seasonal Theme Management

**Status:** Local implementation complete. Owner visual acceptance pending.
**Baseline:** `59558c08bd797b14bd7ada8c647887be1314c340`, the freshly fetched `origin/main` containing Task 04B.
**Branch:** `codex/seasonal-theme-management`. Resolve the local implementation SHA with `git log -1 --format=%H -- docs/implementation/tasks/ADMIN-SEASONAL-THEME-001.md`.

Admin Settings now includes **Landing & User Appearance**. Select a preset, switch the sample between Landing, Login/Register, and Dashboard, then use the confirmation dialog to publish. Preview selection is local to the page. The published label comes from the authenticated API. Publishing Default restores the existing appearance.

| Preset | Visual direction |
| --- | --- |
| `default` | Existing BuddyWeb styles, images, typography, spacing and interactions. The seasonal selector is absent. |
| `halloween` | Spooky Night. Violet surfaces, warm ivory, pumpkin accents, and a static crescent and stars. |
| `christmas` | Winter Celebration. Cream, evergreen and cranberry, with gold trim and hanging ornaments. |
| `summer` | Sunny Campus. Ocean blue, turquoise and sunshine, with a static sun and waves. |

The UI/UX Pro Max skill guided contrast, semantic color pairs, visible focus, responsive layout and low motion. Seasonal tokens activate only when a public or authenticated User layout is present. Portal overlays and session controls inherit those tokens. Admin Login and Admin Dashboard retain their own styling. The Admin samples have a separate selector. The credential-free public read is uncached, and the client uses Default on a missing, invalid or failed response. The active User Side query polls once per minute and revalidates on focus.

`GET /api/public/site-theme` returns only the preset ID. `GET /api/admin/site-theme` and `PUT /api/admin/site-theme` require Admin, and PUT also requires session CSRF. Alembic `0026_site_theme` follows `0025_managed_faq` and creates and seeds one private RLS table. Its check constraint accepts only the four preset IDs. The runtime role can read, seed Default and update the singleton. Publishing locks the row and records `site_theme.publish` in the same transaction with the acting Admin and previous/new preset. Repeating the active preset is a no-op. A separately approved Production release must apply 0026 before activating the matching frontend. No Production action occurred in Task 05.

Changed areas include the site theme client/boundary/CSS, public and User layouts, Admin Settings and EN/DE catalogs, site theme API/migration, Audit Log classification and the loopback review script.

## Phase 2 · Seasonal visual redesign

The frontend redesign is committed locally as `6a7381bbf5d39f46d529c29a1c3360e4489bd406`, directly after the Phase 1 implementation `f11bf6f041aec77d0ace688a35c6083a2a3bd283`. Owner visual acceptance remains open.

| Preset | Typography | Landing illustration and motion |
| --- | --- | --- |
| Halloween | Cinzel headings and Nunito Sans body | Violet moonlight, pumpkin orange, a crescent, a web and pumpkins. Bats drift and stars glow. |
| Christmas | Playfair Display headings and Nunito Sans body | Cream, evergreen, cranberry and gold. Pine, hanging lights, ornaments and a gift frame the campus photo, with sparse falling snow and slowly dimming lights. |
| Summer | Outfit headings and DM Sans body | Sky blue, turquoise and warm sunlight. A sun and tropical leaves frame drifting clouds and moving surf. |
| Default | Existing Poppins and styling | The seasonal illustration and tokens are absent. The original campus slideshow and controls remain available. |

`seasonal-art.css` adds scoped heading and body font, weight and tracking tokens, plus the hero frame, gradient and subtle Login/Register and Dashboard details. Small headings, controls, dialogs and the assistant use the body face. The five locally hosted Latin variable WOFF2 files total about 161 KiB. Each seasonal preset uses two faces and has system fallbacks with `font-display: swap`. Individual SIL Open Font License files are alongside the fonts. [Google Fonts licensing guidance](https://googlefonts.github.io/gf-guide/onboarding.html).

`SeasonalScene` draws the illustrations in one lightweight SVG per Landing hero or Admin preview. Desktop uses at most two independently animated groups per preset. Mobile removes secondary details. The illustrations ignore pointer events and are hidden from assistive technology. Only the Landing illustration animates. The system reduced-motion preference and the existing **Pause page animations** control both stop the seasonal movement. Admin Settings shows the static illustration and type inside its sample only. Admin Login retains Poppins.

The exact `ui-ux-pro` skill was unavailable. The installed `ui-ux-pro-max` supplied the typography, responsive design, contrast and motion guidance.

### Phase 2 review and verification

- Use the startup commands and four links below. Pick a preset on Landing and watch the campus photo for 7–18 seconds, then toggle **Pause page animations**. Try the operating system's reduced-motion setting for the static version.
- In the same tab, visit `/login` or `/register` while signed out. Sign in with the disposable review user for `/user/dashboard` and `/user/settings`. Open **VGU Buddy Assistant** from the dashboard. Use `?theme-preview=live` to clear the preview and see the locally published theme.
- 71 focused frontend tests in six files passed. TypeScript, affected ESLint and Prettier checks, Vite production build and preview marker exclusion passed. The existing large-bundle advisory remains.
- Chromium confirmed animated properties changed over time in each seasonal hero, no seasonal animation ran under reduced motion, and the page pause stopped Halloween's illustration. The four presets loaded on Landing, Login, Register and signed-in Dashboard. Landing and auth had no horizontal overflow at 320px or 390px. Dashboard was checked at desktop and 390px. The Christmas Landing rendered German copy. A Summer preview persisted through navigation to User Settings. The Summer assistant replied and Escape restored focus to its opener.
- A matching screenshot comparison against the approved Phase 1 source found pixel-identical 390px Landing, Login and Dashboard crops, plus desktop Login. Desktop differences were confined to the rotating campus photo and the rasterization of the EN badge in the Dashboard sidebar. Default CSS and the existing slideshow were preserved.
- Admin Login and the Admin Settings shell retained Poppins. The selected Christmas sample used Playfair Display without animation. The synthetic local API published Christmas, served it to the live public view, then published and served Default again. Preview links did not change the published value.
- New browser coverage used Chromium emulation. Physical devices, other browser engines, and full Matching, Invitations, Conversations and Events workflows were not exercised. The Phase 1 backend gates remain the relevant evidence for the unchanged backend.

## Run the local review

Run from the Task 05 worktree. The two Docker commands create dedicated loopback-only services. Skip them if the named review containers are already running. The database and review accounts are disposable. The API script sets its database and Redis URLs explicitly and binds to loopback.

```powershell
docker run --rm -d --name buddyweb-task05-postgres -p 127.0.0.1:64740:5432 -e POSTGRES_DB=buddy_theme_local -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17.11-alpine
docker run --rm -d --name buddyweb-task05-redis -p 127.0.0.1:64741:6379 redis:8.10.1-alpine
```

In an API terminal:

```powershell
Set-Location apps/api
if (!(Test-Path './.venv/Scripts/python.exe')) {
  py -3.12 -m venv .venv
  & ./.venv/Scripts/python.exe -m pip install -r requirements.lock -r requirements-dev.lock
}
$env:PYTHONPATH = (Get-Location).Path
& ./.venv/Scripts/python.exe scripts/seasonal-theme-review.py
```

This worktree can also use the existing Python environment in the original checkout by invoking `C:/Users/phuoc/Downloads/buddyWebVer2/apps/api/.venv/Scripts/python.exe` in the same API terminal.

In a frontend terminal:

```powershell
Set-Location apps/web
if (!(Test-Path './node_modules/.bin/vite.cmd')) { npm ci }
$env:VITE_API_URL = '/api'
$env:LOCAL_API_PROXY_TARGET = 'http://127.0.0.1:5232'
$env:VITE_SEASONAL_PREVIEW = 'true'
$env:VITE_CHATBOT_ENABLED = 'true'
npm run dev -- --host 127.0.0.1 --port 5231 --strictPort
```

| Review surface | URL |
| --- | --- |
| Default | http://127.0.0.1:5231/?theme-preview=default |
| Halloween | http://127.0.0.1:5231/?theme-preview=halloween |
| Christmas | http://127.0.0.1:5231/?theme-preview=christmas |
| Summer | http://127.0.0.1:5231/?theme-preview=summer |
| Published preset, clear preview | http://127.0.0.1:5231/?theme-preview=live |
| Admin Settings | http://localhost:5231/admin/settings |

Use synthetic `theme-user@example.invalid` at `http://127.0.0.1:5231/login` and `theme-admin@example.invalid` at `http://localhost:5231/adminLogin`. Both use the local-only password `ThemeReview!2026`. The two hostnames keep cookies separate. Choose a preview on Landing before navigating to Login/Register or Dashboard. The explicit development-only override persists within the current tab across local navigation and refresh. Open a separate signed-out window to see the Login form if the User is already signed in.

In Admin Settings, preview a theme and verify a tab with the published preset still shows Default. Publish a seasonal preset locally, use the published URL in the User window, and refresh Dashboard. Check Audit Log under Settings. Publish Default and verify the original appearance and unchanged Admin shell.

## Verification and boundaries

- Frontend: 97 focused tests across ten files. Coverage includes preset validation, fallback, active polling and cleanup, focus revalidation, isolated preview, confirmation, restore, Admin guards, login and existing motion/chatbot behavior. Backend: 18 focused tests, including real PostgreSQL 17.11 and the runtime role. Checked the 0025-to-0026 upgrade, default seed, public read, Admin/USER/anonymous authorization, CSRF, invalid payloads, publication, persistence and audit values.
- Chromium local browser coverage includes all four themes on Landing, Login, Register and signed-in Dashboard, desktop and 390/320px overflow checks, EN/DE, local publication, refresh and restore, localized audit entries, Admin scope, Merchandise and Recap, and chatbot question, portal color, Escape and focus return. Calculated text contrast for ten principal palette pairs per seasonal theme. The lowest ratio was 6.63:1.
- Original and Default Login and Dashboard matched in representative captures. Landing differences were confined to the rotating campus image region. The screenshot folder preserves the original baseline and the four local previews.
- Buddy Matching reached the synthetic account's profile readiness gate. Recommendation cards and invitation workflow with a completed profile, physical mobile hardware and non-Chromium browsers were not exercised. Existing motion regression tests cover reduced-motion behavior. Seasonal motifs are static. The web build retains the existing large-bundle advisory.
