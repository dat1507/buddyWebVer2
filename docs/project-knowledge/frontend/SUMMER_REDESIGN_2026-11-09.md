# Summer Redesign - Surf & Beach Holiday

2026-11-09. Local candidate for owner visual acceptance. Task ADMIN-SUMMER-REDESIGN-001.
Production and Git baseline: a4fff542154a38257b160684fb9dd8982bda8716.
Feature branch: codex/summer-theme-redesign.

## Design

Outfit and DM Sans continue to serve EN/DE. The revised palette uses ocean blue for
actions, aqua and sand for surfaces, sunshine yellow for highlights and soft coral
for trim and the striped board. Shared Summer tokens cover public, auth, user and
chatbot UI through the existing boundary. The campus photo, Hero structure and CTAs
stay in their existing positions. A sun and clouds sit above the photo, while the
coral board and coconuts sit on a sandy shelf at its edge. The existing Admin sample
shows static Summer artwork inside the sample card.

Two periodic SVG wave paths translate horizontally along the photo's lower edge at
different speeds and directions. The 240-unit repeat produces a continuous swell.
Mobile animates only the back layer. The front wave and clouds stay static.
Pause freezes the swells at the current frame, and reduced motion keeps the whole
composition static. The artwork is clipped, aria-hidden, unfocusable and
pointer-transparent. No animation timers, external artwork or new dependencies.

## Verification

- 23 focused tests in three suites passed. TypeScript, affected ESLint, Prettier and
  Production build passed. Existing large chunk advisory retained.
- Chromium EN/DE at 1440, 390 and 320 px: campus photo retained, no horizontal
  overflow, visible moving swells, Pause/Resume, reduced motion and reduced mobile
  animation complexity checked. Mobile menu Escape and CTA pointer hit test passed.
- Ten principal semantic foreground/background pairs measured at least 6.35:1.
  This is a token contrast check, not a full-site accessibility audit.
- Default, Halloween and Christmas Hero captures matched the approved baseline
  pixel-for-pixel at 1440 and 390 px after fixing reduced motion and masking the
  carousel images, launcher and local API variability equally on both sides.
- Public Login/Register routes rendered in Summer. Dashboard, chatbot panel and
  Admin Summer sample rendered with temporary browser-only fixtures. Selecting
  Summer showed unpublished status and issued zero publish requests. Existing
  theme tests cover Preview/Publish and restore. Real local sign-in and API-backed
  user flows remain unverified because the disposable database was unavailable.
  No Production session, data or settings used.
- The sampled protected pages cover visual inheritance. Full Matching,
  Invitations, Conversations and Events workflows, physical devices and other
  browser engines were outside the focused checks.

## Owner review

- [Summer Landing](http://127.0.0.1:5240/?theme-preview=summer)
- [Summer Login](http://127.0.0.1:5240/login?theme-preview=summer)
- [Summer Register](http://127.0.0.1:5240/register?theme-preview=summer)

Inspect the photo at desktop and 390/320 px, switch EN/DE and test Pause/Resume
and system reduced motion. Check the Hero CTA and mobile menu remain clickable.
Review captures in the worktree's .local/review directory: summer-1440.png,
summer-390.png, summer-wave.gif, dashboard.png, chatbot.png and admin-preview.png.
For interactive protected fixture review from the worktree, run
`node .local/summer-protected-review.cjs --interactive` while the preview is running.
These fixtures are browser-local. For real local authentication the disposable
review database and API must be available.

Christmas closure and Render assessment are saved separately in local documentation
commit 82a60908cc5edaa57faced50ba1e878fa678b93d on codex/christmas-theme-redesign.
Task 05C is planned for Vietnamese Tet (red/gold/ivory, hoa mai, hoa dao, bao li xi,
gentle animation, Preview/Publish and compatibility review). OPS-DB-BACKUP-001 stays
open before future Production migrations where practical. Task 06 remains planned.
