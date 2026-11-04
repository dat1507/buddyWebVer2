# FE-RECAP-EDITORIAL-001 — Explore More and Recap editorial UI

Status: LOCAL COMPLETE — OWNER VISUAL REVIEW PENDING.

[Implementation and verification](../../project-knowledge/frontend/RECAP_EDITORIAL_UI_2026-11-04.md):
47 focused tests PASS; TS/ESLint/Prettier/build PASS; 16 EN/DE responsive cases, fallback,
keyboard lightbox, focus/44px CTAs/reduced motion verified locally. Protected source unchanged.
No push, main merge, deployment or Production data changes. Local review server port5194.

Owner brief dated 2026-11-04 authorizes frontend-only image-led green/peach Explore More cards,
one unified Recap gallery and a centered editorial detail page. Base: deployed upload fix
7176e09a62b540f3e53ad3f9da68657bb489d1df. Work on codex/recap-editorial-ui in an isolated worktree.

Acceptance: existing public Recap query/cache and signed thumbnail, honest empty/error fallback;
reuse approved Merchandise artwork and Coming Soon state; keep routes, ordered/captioned gallery,
lightbox/keyboard navigation, EN/DE, responsive 1440/768/390/320 layouts and upload regression tests.
No backend/API contract/Storage/migration/auth/retention/Slider change or new dependencies.

Focused source: events-explore-more.tsx, landing.css, recap-story.tsx/recaps.css, recap-photo.tsx
(optional visual fallback only), existing Merchandise artwork and their focused tests. Preserve
Admin upload source. Verify TypeScript/ESLint/build and local visual checks where available.

Strict boundary: commit locally only. No push, merge to main, cloud deployment/settings or
Production-data changes. Backup remains DEFERRED — OWNER-ACCEPTED RISK. Owner local review pending.
