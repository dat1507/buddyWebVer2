# EVENT-FLAG-SPLIT — Separate Admin Event Management and public live Events

- **Status:** RELEASE CANDIDATE — LOCAL GATES PASS / BOTH PRODUCTION FLAGS OFF
- **Priority / track:** P0 product-release / events
- **Owner decision:** 2026-10-11
- **Dependencies:** `ACCEPT-EVENT-001` flag-OFF release; existing Admin RBAC and canonical Event APIs

## Objective

Decouple Admin Event Management from the public live Event experience so each surface can be
activated independently. The frontend switches are build-time release controls; they do not replace
backend authorization.

## Contract

- `VITE_ADMIN_EVENTS_ENABLED` controls Admin Event navigation, list/create/edit routing and Event
  metrics on the Admin overview.
- `VITE_PUBLIC_EVENTS_ENABLED` controls the API-backed Landing slider, public Event detail, User
  Event route/navigation and the User dashboard Event action.
- Only the exact string `true` enables a switch. Missing, empty, malformed, differently cased or
  whitespace-padded values remain OFF.
- The retired `VITE_EVENTS_LAUNCH_ENABLED` value is ignored and cannot enable either new surface.
- With the public switch OFF, Landing renders the same five bundled posters and makes no slider API
  request. With it ON, the existing canonical first-five, EN/DE, retry and empty-state behavior is
  preserved.
- With the Admin switch OFF, every Admin Event route is handled consistently as not found inside the
  ADMIN shell. With it ON, the existing management UI remains behind the ADMIN `RoleGuard` and
  backend ADMIN/RBAC, CSRF, validation and version boundaries.

## Implementation boundary

Frontend configuration, routes, navigation, dashboards, Landing selection, the embedded/global 404
semantic boundary, tests, examples and documentation are in scope. Backend, database, Storage,
Redis, DNS, secrets, canonical Event content and provider configuration are unchanged.

## Verification — 2026-10-11

| Gate                              | Result                                                                                              |
| --------------------------------- | --------------------------------------------------------------------------------------------------- |
| Strict resolver                   | 11 / 11 PASS, including missing, invalid and legacy-true cases                                      |
| Flag matrix                       | OFF/OFF, ON/OFF, OFF/ON and ON/ON: 8 / 8 integration tests PASS per combination                     |
| Additional compatibility matrices | Missing new flags + legacy true and invalid new flags + legacy true: 8 / 8 PASS each                |
| Focused affected tests            | 7 files / 67 tests PASS, plus the resolver suite                                                    |
| Full frontend                     | 85 files / 788 tests PASS on final source                                                           |
| TypeScript / ESLint / Prettier    | PASS / PASS / PASS on final source                                                                  |
| Production builds                 | All four Admin/Public combinations PASS; final OFF/OFF rebuild PASS                                 |
| Final OFF/OFF bundle              | Five static titles retained; slider API and `/admin/events` markers absent                          |
| Accessibility regression          | Global 404 remains `main`; private-shell 404 is a named `section`, avoiding nested `main` landmarks |
| Backend regression                | Not repeated: no backend source or dependency changed; prior CI/backend evidence is reused          |

The existing large JavaScript chunk advisory remains non-blocking and predates this task.

## Production safety boundary

Vercel project/team and the current READY Production deployment were verified before release. The
Production environment contains none of the two new keys and no legacy launch key, so the strict
resolver compiles both surfaces OFF. The current Vercel deployments remain available as rollback
candidates. Render receives no backend change and its accepted `e2ef4c0`/`d15cb1d` rollback evidence
is preserved; no provider mutation is required.

This task does not authorize Admin-only activation, public-live activation or any Production Event
write. The next action requires a separate owner approval to add exactly
`VITE_ADMIN_EVENTS_ENABLED=true` to Production and rebuild Vercel while keeping the public key
absent/OFF. Controlled create/edit/cover acceptance is a later, separately authorized write gate.
