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
