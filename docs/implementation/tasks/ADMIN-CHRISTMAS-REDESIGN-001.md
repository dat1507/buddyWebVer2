# ADMIN-CHRISTMAS-REDESIGN-001 — Snowy & Cozy Wonderland

Status: LOCAL COMPLETE / OWNER VISUAL ACCEPTANCE OPEN — local visual refinement assigned 2026-11-08.
Baseline: f2c2f27754308109d3e92ed3d95383ed1d755b2a, freshly fetched remote main containing released Task 05.
Branch: codex/christmas-theme-redesign. Isolated worktree; all pre-existing work preserved.

Owner contract: Christmas-only palette, existing local Playfair Display / Nunito Sans,
original SVG snow, warm lights, fireplace, Santa and gifts. Landing carries the illustration;
public/auth/User/shared surfaces inherit restrained tokens. Preserve other presets, Admin,
theme IDs, persistence, authorization, Publish/Audit APIs, database and runtime configuration.
Respect reduced motion and page pause, keyboard access, contrast and 390/320px widths.
Provide running local preview, desktop/mobile captures, browser animation checks, focused tests,
TypeScript/lint/format/build and Default comparison. Update Project Knowledge and commit locally.
No push, merge, deploy, migrations or Production mutation. Owner visual acceptance follows.

Implementation paths: apps/web/src/features/site-theme/{christmas-scene.tsx,seasonal-scene.tsx,
seasonal-art.css,seasonal-theme.css}; apps/web/src/components/landing/hero-section.tsx.
Focused existing tests: site-theme.test.tsx, landing motion/hero tests, auth and chatbot tests.

## Completion evidence — 2026-11-08

Local verification PASS. [Project Knowledge and review instructions](../../project-knowledge/frontend/CHRISTMAS_REDESIGN_2026-11-08.md)
contain the final design, exact test evidence, 14 identical comparison captures,
responsive/motion/contrast results, Admin preview plus Cancel/Escape, limitations,
local URLs and screenshots. Existing 63-test/type/lint/format/build evidence reused;
final copy/mobile changes additionally passed theme tests, format and build.

Local branch remains based on released f2c2f27. One focused local implementation
commit contains this record; resolve its full SHA with `git log -1 --format=%H`.
No push, merge, deployment, migration, theme publication or Production changes.
Task remains at owner visual acceptance; do not begin release without a new request.


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
