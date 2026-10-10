# ACCEPT-EVENT-001 Production code release evidence — 2026-10-10

## Authorization and boundary

The owner authorized a direct-to-`main` frontend/backend code deployment only after Local A–E,
Quality Gate E and executable rollback preflight passed. This release keeps
`VITE_EVENTS_LAUNCH_ENABLED` OFF. It does not authorize Production Event writes, seed/publication,
provider/secret changes, database mutation, destructive recovery or Event launch.

## Production preflight — PASS

| Check | Direct evidence before push |
| --- | --- |
| Source candidate | Local `main` at `e2ef4c0cca7137ff319faa95d8e82672b0cc3bfc`; tracked tree clean |
| Vercel baseline | Production `dpl_BZ6CeLDAGQDoMhVcz3BtEYgsTaUG`, Git SHA `253849d`; READY |
| Render baseline | Service `srv-db343ne7bikc73bjv910`; live deploy `dep-db343nu7bikc73bjvalg`; Git SHA `d15cb1d` |
| Public frontend | 200; bundle `index-CC-xLBAH.js` contains all five static titles and no canonical slider/Admin Event API marker |
| API boundary | live 200; ready 200 with database/Redis `ok` and email/Storage `configured`; anonymous auth 401/no-store |
| Pre-release Event API | public Event list and slider both 404, consistent with the old backend candidate |
| CORS | exact first-party login preflight 200 with credentials enabled |
| Production database | Supabase ACTIVE_HEALTHY; Alembic `0021_restore_runtime_permissions`; `app_private.events` and `app_private.event_media` present |
| Event Storage | private `event-media`; 5 MiB limit; JPEG/PNG/WebP allowlist |
| Migration delta | None; Event tables/bucket predate the live backend commit |
| Launch flag | No explicit Vercel `VITE_EVENTS_LAUNCH_ENABLED` entry; Production default is OFF and the deployed bundle proves the static path |

The Render service tracks `main`, uses root directory `apps/api`, its Dockerfile, and Auto-Deploy
`On Commit`. Vercel tracks the same repository/branch with root directory `apps/web`. Deployment
order may differ, but the candidate is skew-safe: backend changes are additive, and the flag-OFF
frontend retains the static five-poster path without requesting canonical Event APIs or advertising
Admin Event routes.

## Rollback readiness — PASS

- Vercel exposes READY rollback candidates, including
  `dpl_G7Kn9dMw3YyM7dk1VgQmsKzYfWr1` at `c2fbaf1`. Provider rollback is available without rebuilding
  the Event candidate.
- Render had only one retained deploy before push, but its read-only `Deploy a specific commit`
  flow found `d15cb1d7c380e12e8f66e38f5573d191415d6913`; selecting it enabled `Deploy Commit`. The modal was
  cancelled without deployment. This is an executable immutable redeploy path using the existing
  service configuration and database-compatible source. Render warns that using this path disables
  Auto-Deploy to prevent an immediate overwrite, so an operator must restore the intended setting
  after a rollback decision.
- No migration is added, so code rollback does not require a database downgrade. The database
  remains at head `0021`; destructive restore/downgrade is outside this release.

## Deployment and smoke

`origin/main` accepted `253849d..e2ef4c0`. GitHub CI, Vercel deployment
`dpl_Evhx9hudQSBf99P9fxznxtGNg2GS` and Render deployment
`dep-db4v9lqvcj2c73e5jvlg` started from `e2ef4c0`.

All three reached terminal success:

| Gate | Result |
| --- | --- |
| GitHub Actions | Run `38037425291` SUCCESS; Backend SUCCESS; Frontend SUCCESS |
| Vercel | `dpl_Evhx9hudQSBf99P9fxznxtGNg2GS` READY at `e2ef4c0`; Production aliases attached |
| Render | `dep-db4v9lqvcj2c73e5jvlg` LIVE at `e2ef4c0`; prior `d15cb1d` deploy exposes a native Rollback action |
| API health | live 200; ready 200 with database/Redis `ok` and email/Storage `configured` |
| Public canonical Event API | slider 200 `[]`; list 200 with total 0; nonexistent detail 404; all no-store |
| Authorization boundary | anonymous Admin Event list 401/no-store; local USER/anonymous write-denial acceptance remains the full mutation evidence |
| Frontend/flag | bundle `index-phrHnhsS.js`; all five static titles present; canonical slider and Admin Event API markers absent |
| Browser Landing | static five-poster carousel visible on desktop/mobile; responsive navigation intact; zero console warnings/errors |
| Existing USER session | protected Profile and Buddy Matching read paths loaded with no alert or console warning/error |
| Admin Event UI | intentionally hidden by flag OFF; direct `/admin/events` rendered the 404 boundary, not the Admin editor |
| Event Detail UI | NOT RUN in Production because canonical Event total is zero and the flag-OFF route is intentionally absent |
| Production writes | 0 Event/account/Storage/database writes; no seed, publish, cancellation, flag or provider setting change |

The existing USER browser session was reused only for protected read paths; no credential was
entered, no form was submitted and the session was not logged out. No ADMIN session was available,
so an authenticated Admin Event render is correctly reported as NOT RUN rather than inferred.

## Result

**DEPLOYED — FLAG-OFF PRODUCTION SMOKE PASS / AWAITING EVENT LAUNCH APPROVAL.** The code release is
healthy and rollback-ready. Live Event launch remains blocked until owner-approved canonical data
exists and the owner separately authorizes changing the Production flag. No launch action is part
of this record.
