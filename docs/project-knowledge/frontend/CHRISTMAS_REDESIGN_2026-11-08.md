# ADMIN-CHRISTMAS-REDESIGN-001 — Snowy & Cozy Wonderland

Date: 2026-11-08 (Asia/Saigon). Local implementation; owner visual acceptance pending.

## Design and implementation

Christmas uses snow white and ice/powder blue surfaces, dark blue-gray text,
burgundy actions and restrained champagne/amber accents. Light blue replaces the
previous dark evergreen bands, including the User welcome card and public footer.
Playfair Display headings and Nunito Sans body reuse the two existing self-hosted
EN/DE WOFF2 assets (about 69.5 kB total), their existing font-display/fallback setup,
and reserved artwork dimensions. No new font requests or image dependencies.

The original SVG illustration presents Santa, gifts, snow-covered trees and a
stone fireplace as one scene beneath the existing campus photo. Nine connected
warm bulbs shimmer at staggered intervals. Two snowfall layers drift downward;
the flame scales subtly and its glow changes opacity. The scene preserves its
aspect ratio. At narrow widths it hides half the snow particles and places the
resource link beneath the illustration. Functional pages use existing shared
seasonal tokens, without large artwork or continuous decoration.

The installed ui-ux-pro-max checklist guided contrast, focus, restrained motion,
semantic colors and responsive layout. Its broad palette/font search did not
match the approved winter direction; the explicit owner palette and existing
Playfair Display/Nunito Sans pairing take precedence. React review found no new
hooks, state, listeners, requests, animation timers or dependencies.

Only Christmas tokens, artwork, its conditional Hero placement, and the Christmas
EN/DE descriptions change. Default, Halloween and Summer styling/artwork remain
unchanged. Theme IDs, persistence, preview boundary, Admin authorization, Publish
API, Audit Log, Admin shell/Login, backend, migrations, dependency locks and runtime
configuration are untouched. Original worktrees and unpublished commits remain.

## Verification

- Exact lockfile installed in this isolated worktree. Six focused suites passed:
  63 tests covering theme selection/publication, Landing, page pause, slideshow,
  Login and chatbot. After the final mobile spacing/copy edits, all six theme tests
  passed again. TypeScript, affected ESLint, seven-file Prettier and final Vite
  build passed. The existing >500 kB bundle advisory remains.
- Production bundle contains neither the local preview URL marker nor its session
  storage key. Local preview remains development-only.
- Chromium exercised Landing, Login, Register and signed-in Dashboard in EN/DE at
  1440, 390 and 320 px, with no horizontal overflow. The synthetic local account
  uses the existing disposable Task 05 database. No migration or new account was
  created. No Production endpoint was used.
- Browser-computed styles changed over time for snow, bulbs and flame. The page
  pause button froze all three at the current frame. Reduced motion produced zero
  animations inside the scene. Mobile hid the extra snow particles. Decorations
  remain aria-hidden, nonfocusable and pointer-events:none. Chatbot Escape returned
  focus to its launcher.
- Twelve matched Default/Halloween/Summer Landing and Login captures at desktop
  and 390 px were pixel-identical to Task 05. The rotating campus photo was masked
  equally in both versions to avoid timing differences. All other pixels were
  compared, including the seasonal artwork. This is a representative visual
  regression check, not a claim about every possible data state.
- Browser preview generated no theme write request; the local public API continued
  returning Default. The existing publication/authorization tests remain passing.

- Admin Settings selected Christmas correctly. Cancel and Escape closed the
  publication confirmation while preserving the local selection. No theme write
  occurred and the public local API still returned Default. Admin shell typography
  and color remained unchanged; Admin Login retained Poppins. The sample is static.
- Two additional Default Dashboard comparisons (1440/390px) were pixel-identical,
  bringing the matched comparison total to 14. A real local chatbot request returned
  a sourced matching explanation. Profile, My Buddies, Recap and Merchandise rendered.
- Ten principal text/background pairs measured 5.22:1 to 11.17:1. Observed cold-page
  cumulative layout shift was 0.0012; this is one local observation, not a performance
  guarantee. Final mobile artwork/resource-link separation passed at 390/320px.
- Limitations: Chromium only, no physical-device checks. Matching reached the existing
  synthetic account's profile-readiness gate; populated invitation/conversation
  workflows were not exercised. Event feature flags were not enabled in this local
  review, so canonical Event list/detail rendering is unverified. Early guessed
  route probes returning Not Found are not accepted as surface verification; the
  later correct Profile/My Buddies/Recap/Merchandise checks supersede those probes.
  All applicable shared tokens are scoped through the unchanged theme boundary.
- Resume verification reused all successful application checks. Only Cancel/Escape
  and current preview availability were newly exercised; no source changed on resume.
  Review URL returned HTTP 200. No full regression suite was repeated.

## Local review

The isolated worktree is `.local/worktrees/christmas-theme-redesign` beneath the
original repository. The frontend runs on loopback port 5235 and its API on 5232;
the unchanged comparison frontend runs on 5236. The existing disposable services
use loopback ports 64740 (PostgreSQL) and 64741 (Redis). No Production settings changed.

- [Christmas Landing](http://127.0.0.1:5235/?theme-preview=christmas)
- [Christmas Login](http://127.0.0.1:5235/login?theme-preview=christmas)
- [Christmas Register](http://127.0.0.1:5235/register?theme-preview=christmas)
- [Christmas Dashboard](http://127.0.0.1:5235/user/dashboard?theme-preview=christmas)
- [Default comparison](http://127.0.0.1:5235/?theme-preview=default)
- [Admin Settings](http://127.0.0.1:5235/admin/settings)

Use the existing synthetic review accounts documented in
[Task 05](../../implementation/tasks/ADMIN-SEASONAL-THEME-001.md#run-the-local-review).
Preview persists in the current tab. Use `?theme-preview=live` to clear it.
Open the assistant using the lower-right launcher. On Landing, watch the lights,
snow and fireplace for at least six seconds, then toggle **Pause page animations**.
The operating system's reduced-motion preference provides the static version.

Local evidence is retained in this worktree's `.local/review/`:
`christmas-desktop.png`, `christmas-mobile-390.png`, `christmas-mobile-320.png`,
`christmas-en-1440-dashboard.png`, `christmas-chatbot-390.png`,
`christmas-animation.gif`, EN/DE page captures and JSON browser reports.
The GIF records rendered browser frames; it is not a substitute for live timing review.
The ignored `.local/review-api.py` starts the existing local API without running
migrations, and `.local/review.cjs` / `.local/additional.cjs` preserve browser checks.

For frontend restart, run from this worktree's `apps/web`:

```powershell
$env:VITE_API_URL='/api'
$env:LOCAL_API_PROXY_TARGET='http://127.0.0.1:5232'
$env:VITE_SEASONAL_PREVIEW='true'
$env:VITE_CHATBOT_ENABLED='true'
npm run dev -- --host 127.0.0.1 --port 5235 --strictPort
```

## Git and next step

Baseline: `f2c2f27754308109d3e92ed3d95383ed1d755b2a`, freshly fetched remote main
containing the Task 05 release. Branch: `codex/christmas-theme-redesign`.
The focused local commit contains this record; resolve it with `git log -1 --format=%H`.
Stop after the local commit. No push, merge, deployment, migration, publication,
Production data/provider/secret change is authorized or performed. Ready for owner
visual acceptance; deployment needs a separate owner request.


## 2026-11-08 - Landing refinement supersedes illustrated Hero

Owner requested removal of the Santa/fireplace/gift panel from Landing. This revision
restores original Hero photo proportions, caption and resource-link layout while keeping
the approved Christmas palette and typography. Original artwork remains in the existing
Admin sample only; it is no longer mounted on Landing.

New ChristmasLandingEffects mounts only for Christmas Landing: 24 stylized six-arm
SVG snowflakes, deterministically scattered with varied size, negative start delays,
15-29 second fall durations and horizontal drift. Mobile shows 10 flakes. A draped
navbar garland uses green/red/yellow bulbs and staggered 4.8-second opacity twinkles.
Decorations are pointer-transparent, aria-hidden and excluded from tab navigation.
Snow starts beneath the navbar; lights sit below its boundary without layout space.
Only transforms and opacity animate; there are no timers or external assets.
Reduced motion hides falling snow and leaves static lights. Page pause freezes both.

Focused verification: EN/DE at 1440/390/320px, no horizontal overflow, no illustrated
Landing panel; actual snow/light animation and pause frozen-state checks PASS.
Reduced motion has zero effect animations; mobile menu opens and Escape closes.
Default/Halloween/Summer mount no Christmas effects; their source styling unchanged.
Prior unrelated auth/User/Admin/publish and other-preset evidence is reused.
No backend, persistence, environment, database or Production changes.

Review: http://127.0.0.1:5235/?theme-preview=christmas . Updated screenshots and animation:
`.local/review/revision/en-1440.png`, `en-390.png`, `en-320.png`, DE equivalents,
`animation.gif` and `results.json` in the same folder. Watch the sparse flakes and
bulbs, pause/resume, enable system reduced motion, and open mobile navigation.
Verify Hero text/CTA remain readable and clickable. Physical devices and non-Chromium
engines remain unverified. Owner visual acceptance is pending; no push/merge/deploy.


Revision checks: 17/17 focused Landing/motion tests PASS after updating the old
illustration assertion to check the replacement effects and pause wiring. TypeScript,
affected ESLint and Prettier PASS. Vite build PASS with existing chunk advisory.
The final Christmas gradient retains background-size:cover to prevent repetition.
Prior initial test failure was an obsolete illustration assertion, now corrected.
