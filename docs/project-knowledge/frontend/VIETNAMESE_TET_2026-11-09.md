# Vietnamese Tết - Elegant Spring Celebration

Task ADMIN-VIETNAMESE-TET-THEME-001. Local candidate, 2026-11-09.
Base 55e82608e884be705eeef82529feff82c341538d, verified against remote main and
the Production Vercel alias. Summer owner closure is documented separately.

## Design and implementation

Ivory and cream surfaces, festive red actions, dark warm ink, gold details, peach
pink, apricot yellow and restrained leaf green. Georgia and Segoe UI with serif
and sans-serif fallbacks use installed fonts, with no new font download. The EN/DE
preset names retain the Vietnamese diacritics in Tết.

The original campus photo and CTA composition frame original five-petal hoa mai
and hoa đào on separate branches. Two red bao lì xì have gold seams and ornament.
Twelve deterministic petal positions, mixed sizes, colors, delays and drift yield
gentle fall. Mobile draws six petals. One envelope sways. Motion is CSS-only and
clipped to the existing photo frame. The existing Pause control freezes motion.
Reduced motion and the Admin sample are static. The SVG is hidden from assistive
technology and ignores pointer input. Shared seasonal tokens give functional
pages a restrained treatment without adding illustration layers.

The existing preset registry drives the fifth Admin card, Preview and local
preview override. The existing API Literal gains tet. PostgreSQL migration
0027_site_theme_tet follows 0026_site_theme and widens the named CHECK constraint
without updating data. Its single ALTER statement preserves the singleton,
Default seed, RLS policies and grants. Public read, Admin authorization, CSRF,
publish locking and audit writes reuse the existing paths.

## Local evidence

- 23 frontend tests across three suites. TypeScript, affected ESLint, Prettier and
  Vite build passed. The existing bundle size advisory remains.
- 11 backend theme/migration tests passed with real disposable PostgreSQL 17.
  Upgrade from 0026 preserved the existing Summer row. Real API tests exercised
  publish, restore, public read, Admin authorization, CSRF, invalid input,
  duplicate-publish no-op and ordered audit values. Two additional Recap migration-
  head checks passed on a separate disposable database. Targeted Ruff lint and
  formatting passed.
- SQL inspection confirmed revision 0027_site_theme_tet, the five-value CHECK,
  RLS and all three existing policies. Runtime SELECT/UPDATE allowed and DELETE
  denied. A direct invalid-ID update failed at the CHECK constraint.
- Chromium passed EN/DE Landing at 1440, 390 and 320 px with the campus photo
  present, no horizontal overflow, and mobile menu and CTA usable. Petals move
  and freeze on Pause, envelope pauses, reduced motion is static, and mobile
  renders half the petals. Ten semantic text pairs measured at least 7.22:1.
- Eight controlled Hero comparisons for Default, Halloween, Christmas and Summer
  matched pixel-for-pixel at 1440 and 390 px with reduced motion, photo and launcher
  masking, and equivalent API interception. Prior scene implementations remain.
- Local Login/Register, synthetic signed-in Dashboard and chatbot panel rendered.
  Real synthetic Admin showed five presets and EN/DE Tết labels. Preview remained
  local and sent zero PUT requests. A separate disposable browser Publish/Restore
  issued two PUT requests, recorded Default to Tết to Default in the audit log
  and left Default stored. No Production account or database participated.
- Physical devices, alternate browser engines, and full Matching, Invitations,
  Conversations, Events and chatbot answer workflows were outside focused checks.

## Owner review

- [Tết Landing](http://127.0.0.1:5242/?theme-preview=tet)
- [Tết Login](http://127.0.0.1:5242/login?theme-preview=tet)
- [Tết Register](http://127.0.0.1:5242/register?theme-preview=tet)
- [User Dashboard](http://127.0.0.1:5242/user/dashboard?theme-preview=tet), then open the chatbot.
- [Admin Settings](http://127.0.0.1:5242/admin/settings), select Tết in Theme presets.

Use the local synthetic accounts defined in
[the review script](../../../apps/api/scripts/seasonal-theme-review.py). Use separate
browser profiles for User and Admin, or sign out of one before testing the other.
Check English and German, desktop and mobile, Pause/Resume and system reduced motion.
The stored local theme can be checked with /api/public/site-theme. Select a preset
without confirming Publish to review the Admin preview safely.

The local frontend listens on 5242 and API on 5243. The isolated PostgreSQL cluster
binds only to 127.0.0.1:55473, with its data under .local/tet-pg. The adapted local API
launcher is .local/tet-review-api.py. The Vite process uses VITE_API_URL=/api,
LOCAL_API_PROXY_TARGET=http://127.0.0.1:5243, VITE_SEASONAL_PREVIEW=true and
VITE_CHATBOT_ENABLED=true. No local Redis is required for these theme smoke checks.
Captures under .local/review: tet-1440.png, tet-390.png, tet-motion.gif, dashboard.png,
chatbot.png, admin-preview.png and admin-preview-de.png.

## Future release dependency

Obtain separate release approval. Verify recovery readiness and apply 0027 before
an API accepts or stores tet. Deploy the compatible API before making Publish
available in the new frontend. An older API cannot deserialize a stored tet value.
Any later application rollback to that API must first ensure an earlier preset
through the authorized workflow. The migration is forward-only. Keep the published
Production theme under the owner's control.


## 2026-11-09 - Navbar fireworks refinement

The public Tết Navbar has a dotted gold trail, warm red and gold ray clusters and
small particles. The strip sits within the bottom edge of the sticky header,
using the existing space below the controls. It takes no layout space, is
pointer-transparent and aria-hidden, and contains eleven bursts on desktop and
five on mobile. A staggered CSS opacity/scale cycle animates on Landing. The
existing Landing pause state freezes the current frame. Reduced motion and
other public routes show a static strip. No scroll tracking or React animation
loop. The existing Tết artwork, palette and photo composition are preserved.

40 focused Navbar/Landing/motion/theme tests passed. TypeScript, affected
ESLint, Prettier and Vite build passed. The existing bundle advisory remains.
Chromium at 1440, 390 and 320 px verified sticky placement, no horizontal
overflow, clear controls, desktop language/sign-in controls, mobile menu Escape,
Pause/Resume, static reduced motion and static Login. The strip is absent from
Default, Halloween, Christmas and Summer. Eight Navbar captures matched the
previous baseline pixel-for-pixel at 1440 and 390 px. Local public API still
reported stored Default. Browser probes used intercepted
anonymous API responses. Backend and migration checks from the initial
implementation were reused. No publish requests or Production changes.

Review: http://127.0.0.1:5242/?theme-preview=tet
Local captures in .local/review/fireworks: navbar-1440.png, navbar-390.png and
navbar-fireworks.gif. Scroll with the menu closed, open the mobile menu and
try Escape, then test Pause/Resume and system reduced motion.

### Scroll effects for owner approval

These options are proposals. The current refinement contains only the Navbar strip.

| Option | Visual fit and impact | Cost and placement | Responsive and accessibility |
| --- | --- | --- | --- |
| A. Floating blossom petals | Strong continuity with hoa mai and hoa đào. Light movement between sections. | Low with a handful of transformed SVG petals. Clip to selected section edges. Optional shallow scroll response on desktop. | Keep petals in gutters and away from text. Reduce count or use a static accent on mobile. |
| B. Floating lucky envelopes | Recognizable Tết symbol, but repeated envelopes would compete with the Hero ornament. | Low rendering cost, higher collision risk. Prefer one section-scoped ornament. Fixed edges would compete with controls. | Keep out of the CTA, chatbot and menu zones. Static on mobile if used. |
| C. Golden cloud parallax | Calm, traditional texture that pairs with the gold trim. | Low as a static SVG. Parallax adds coordination and a larger moving area. Scope to a section background. | Keep the contrast low around reading areas and use static clouds on mobile and reduced motion. |
| D. Firework sparkles | Links section transitions to the Navbar motif. Best as a tiny, brief accent. | Low with a single entry trigger per selected section and opacity/scale only. Avoid repeated triggers. | Keep away from copy and controls. Skip when reduced motion or Pause is active. |

Recommendation: start with A and use D sparingly on desktop at one or two
section entrances. Give each visible area one moving accent at a time, with
static accents for mobile or reduced motion. Keep C available as a static
alternative and reserve envelopes for the Hero. Avoid fixed viewport overlays.

## 2026-11-09 - Approved Landing scroll effects

Explore More and About carry both approved effects. Blossom Scroll Drift reuses
the campus scene's two petal silhouettes and colors. Each section has six petals
on desktop, four on tablet and two static petals on phones. The petals sit in
the side gutters. The offset runs from about +18 to -18 px as a desktop section
passes through the viewport, with a maximum of ±8 px on tablet. A slight CSS
breeze varies their rotation and horizontal position.

Festive Section Sparkles adds a small three-star gold cluster to the right edge
of Explore More and the left edge of About. Each cluster scales and fades over
1.05 seconds the first time its corner enters view on desktop or tablet.
Reload the page to repeat the review. Phone widths and system reduced motion
show static petal accents. The Hero and Navbar retain their existing artwork
and motion.

Pause page animations freezes petal drift and any sparkle already playing.
Resume continues that sparkle and lets a newly visible section play once. A
section passed while paused only plays if its corner is visible after resuming
or enters view later. Reduced motion disables drift and hides the sparkles.
Decorations are clipped to their section, hidden from assistive technology
and transparent to pointers. Passive scroll listeners coalesce updates with
requestAnimationFrame and write an offset only while the section is visible.
IntersectionObserver disconnects after each burst. Both features stop
tracking while paused and clean up on unmount.

### Verification

Thirty focused frontend tests, TypeScript, targeted ESLint and Prettier, and
the Vite production build passed. The existing bundle advisory remains.
Chromium passed EN/DE at 1440, 900, 390 and 320 px for gutter placement,
controls, overflow, and Navbar animation. Desktop checks confirmed parallax,
section entry, one burst per section, pause/resume, and live reduced motion.
The German Admin Settings preview passed against the local API. No Publish
request was sent and the saved theme was still Default.

Explore More and About matched the Summer release baseline for Default,
Halloween, Christmas and Summer at 1440 and 390 px. Captures excluded the
sticky Navbar and chatbot and masked the About photo, which showed minor
browser resampling differences. The photo asset is identical to the baseline.
The local Tết preview returned HTTP 200. All 266 task files and index links
were validated.

### Owner acceptance

Open the [local Tết Landing](http://127.0.0.1:5242/?theme-preview=tet). On a
desktop or tablet, scroll slowly from Upcoming Events into Explore More, then
into About. Look at the outer gutters for the moving apricot and peach petals
and each small gold sparkle. Scroll back through both sections to confirm the
sparkles play once. The Hero's Pause page animations button pauses the effects.
To check reduced motion, turn on the operating system's reduced-motion setting
and reload. The browser's reduced-motion emulation also works.

Review artifacts in the worktree's .local/review/scroll-effects directory
include landing-desktop.png, landing-mobile.png, drift.gif and sparkle.gif.
The sparkle recording samples one triggered CSS animation. The GIF loops for
review, while the effect in the page plays once per section.
