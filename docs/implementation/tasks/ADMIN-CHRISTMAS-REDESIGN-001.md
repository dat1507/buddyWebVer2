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
