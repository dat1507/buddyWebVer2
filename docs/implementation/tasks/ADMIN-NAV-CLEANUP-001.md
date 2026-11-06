# ADMIN-NAV-CLEANUP-001 — Admin Navigation Cleanup

Status: DONE — LOCAL VERIFIED, 2026-11-06. No release authorized.

## Contract and result

Owner assigns a focused frontend cleanup: remove Announcements, Campus and Analytics from the
shared desktop/mobile Admin menu; preserve all other modules, localization, layout and guards.
The eight links, with the existing Admin Events flag enabled, remain Overview, Users, Matching,
Semesters, Events, Knowledge Base, Audit Log and Settings in that order. The existing flag-OFF
configuration retains seven links; this task does not enable Events or modify configuration.

Actual legacy paths `/admin/announcements`, `/admin/campus` and `/admin/analytics` now use
React Router `Navigate` with `replace` to `/admin/dashboard`. Obsolete query/hash state is dropped.
Redirects sit inside the unchanged ADMIN RoleGuard and AdminLayout. Anonymous access still goes
to `/adminLogin`; USER access still goes to `/`. Session bootstrap continues to gate rendering.
No nested legacy routes existed; no wildcard routes were added. Remaining placeholder pages stay.

NavLink route matching and shared focus-visible styling were already correct and remain unchanged.
Browser proof showed Overview active while Users independently had the visible orange focus ring.
Backend services/data, metrics collection, public Campus Resources, authentication implementation,
matching, Events/Recap implementation, AI, database/schema and dependencies are unchanged.

## Files changed

- `apps/web/src/routes/admin-routes.ts`: remove three registry entries and unused icons.
- `apps/web/src/App.tsx`: three explicit guarded legacy redirects.
- `apps/web/src/components/layout/admin-sidebar-navigation.test.tsx`: exact EN/DE menu contract.
- `apps/web/src/components/layout/admin-sidebar-integration.test.tsx`: redirects, authorization,
  bootstrap, existing destination and localization regression coverage.
- `apps/web/src/components/layout/admin-layout-integration.test.tsx`: legacy route expectation.
- This task, `SESSION_HANDOFF.md`, `implementation-plan.md`, `docs/implementation/task-index.md`,
  `docs/implementation/validation.md`, `docs/project-knowledge/frontend/README.md`: task evidence/routing.

## Verification

- Focused four Admin navigation/layout suites: Events ON 42 PASS; Events OFF 41 PASS.
- TypeScript (`npm run typecheck`), targeted ESLint/Prettier, Events-ON production build: PASS.
  Existing large-chunk advisory only. Initial sandbox temp-file ENOENT recovered by local TEMP/TMP.
- Brave local browser, synthetic Admin API fixture only: desktop measured 1600 CSS px and mobile
  390 CSS px; EN/DE eight-link menu, no horizontal overflow on checked Overview/menu views.
- Keyboard activation reached all eight original destinations; Users, Matching and Events rendered
  empty synthetic lists, placeholders preserved. Semester navigation reached its existing route;
  its backend operation/status acceptance is outside this fixture's scope.
- All three legacy URLs settled at Overview; one sidebar current link. Refresh retained correct
  state. Back returned from redirected Overview to preceding Settings; Forward returned to Overview,
  proving replacement rather than another legacy history entry. No redirect loop.
- Focus-visible Users ring (2px offset/2px orange ring) differed from filled Overview active state.
- Browser captured error/warning logs empty after fixture setup. Initial missing-local-API error
  preceded the fixture; no Production access. Desktop screenshot export timed out; mobile evidence
  retained in ignored `.local/mobile-de.png`. No screenshot export PASS claimed for desktop.
- Mobile pointer automation did not activate links under touch emulation; all eight browser links
  were verified by keyboard, and actual sidebar click behavior is covered in integration tests.
  Real account/backend acceptance and mobile touch-device interaction were not performed.

## Git and local review

Base: `c4f6227322792f7dba6d6b0db3cdef18852ab055` (documented release and local origin/main).
Branch: `codex/admin-navigation-cleanup`; isolated `.local/worktrees/admin-navigation-cleanup`.
Commit reference: the single commit containing this record; resolve full SHA with
`git log -1 --format=%H codex/admin-navigation-cleanup`. The final report records its exact SHA.
Original dirty `codex/pillow-security-fix` worktree and all other branches remain intact.
No push, main merge, deployment, provider/secret/account/database changes.

Preview: `http://127.0.0.1:5197/admin/dashboard` with a localhost-only synthetic read-only API on5198.
No credentials required while the fixture is running. To restart, from this worktree run
`python .local/admin-fixture.py` in one terminal. In `apps/web` set PowerShell environment variables
`$env:VITE_ADMIN_EVENTS_ENABLED='true'`, `$env:VITE_API_URL='/api'`,
`$env:LOCAL_API_PROXY_TARGET='http://127.0.0.1:5198'`, then
`npm run dev -- --host 127.0.0.1 --port 5197 --strictPort`.
Fixture/evidence are ignored local files, not production assets. Inspect menu, switch EN/DE, visit
three legacy paths directly, then check Settings -> legacy URL -> Back/Forward and keyboard Tab.
