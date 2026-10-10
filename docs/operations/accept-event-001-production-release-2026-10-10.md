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

## Final verification and launch-preparation addendum

The docs-only follow-up commit `e0ef3439fa9c7b1dec091cd030326fbf4ac308aa` reached
`origin/main`. GitHub Actions run `38038014039` completed with Backend SUCCESS and Frontend
SUCCESS. Vercel deployment `dpl_3ndKHjjd57dNtye1X1k3Sw2Pd5HY` is READY at that docs SHA, while
Production still serves the accepted application bundle `index-phrHnhsS.js`: all five static
titles are present and canonical slider/Admin Event API markers are absent. The public site,
API live and API readiness endpoints return 200.

Render did not deploy the docs-only commit. Service `srv-db343ne7bikc73bjv910` still shows
`dep-db4v9lqvcj2c73e5jvlg` LIVE at application SHA `e2ef4c0`, retains prior deploy
`dep-db343nu7bikc73bjvalg`, and exposes Rollback. A direct read-only Production query confirmed
`app_private.events` contains zero rows: zero DRAFT, PUBLISHED and CANCELLED records and zero
records with a cover. The public slider also remains 200 `[]`.

### Current feature-flag topology

- `VITE_EVENTS_LAUNCH_ENABLED` is the only launch switch. It is absent from the Vercel Production
  environment, so the production build default is OFF.
- The switch is compiled by Vite and controls the Landing live slider, public Event Detail route,
  User Event route/navigation/dashboard action, Admin Event list/navigation, and Event metrics on
  the Admin overview.
- The Admin create and edit child routes are currently registered behind the ADMIN role guard but
  outside the launch-flag condition. They are not exposed through the flag-OFF Admin list/navigation,
  but an ADMIN with a direct URL could reach them. This is an architecture inconsistency, not
  authorization to use those routes in Production.
- Admin management and public launch therefore cannot be enabled independently as a supported
  flag-only operation. Turning the current switch ON would also replace the static Landing carousel
  and expose public/User Event surfaces.
- Because the flag is a `VITE_` build-time value, a Vercel rebuild/deployment is required for a
  change. Render does not need a restart: the deployed backend APIs are already active and retain
  their ADMIN/RBAC, CSRF, versioning and validation boundaries.

The minimum safe Phase A design is a separately approved code task that introduces an Admin-only
switch and a public-live switch, applies the Admin switch consistently to list/create/edit routes,
navigation and metrics, and leaves the public switch OFF. No such refactor or deployment was made
in this session.

### Canonical data checklist

The five committed JPEG posters, titles and localized poster-alt text are reusable. Production has
no canonical Event rows. The owner must supply or explicitly approve, without inference from the
posters:

- EN and DE title, description and location;
- start and end local date/time plus the intended IANA timezone;
- visibility and whether the record should remain DRAFT or be PUBLISHED;
- organizer/category when desired;
- registration URL, registration enabled state, capacity and deadline when applicable;
- final cover selection and EN/DE cover-alt text.

A DRAFT may be incomplete and defaults to MEMBERS visibility. Publication requires non-empty EN/DE
title, description and location, a valid start/end order, and a READY cover owned by the Event.
JPEG/PNG/WebP covers up to 5 MiB are supported. The current project-owned JPEG files are all below
200 KiB, but their content, dates and ownership approval still require human review.

### Activation order

1. Approve and implement the independent Admin/public flag design; keep both Production flags OFF.
2. Deploy the flag split with the existing static carousel unchanged and verify rollback.
3. Separately authorize Admin-only activation, then create owner-approved DRAFT records through the
   product UI; do not publish test content.
4. Run controlled Production write acceptance for create/edit/cover replacement and verify that the
   public slider remains static.
5. Owner reviews the canonical records and explicitly approves any publication.
6. Obtain a separate Live Slider approval, enable only the public switch, rebuild Vercel, and smoke
   the first five qualifying PUBLIC/PUBLISHED/upcoming Events.
7. On frontend regression, restore the OFF/static build or promote the accepted deployment. On
   backend regression, use Render native rollback to `d15cb1d`; no database downgrade is required.

No Production write, publication, flag, secret, provider setting, database, Redis or Storage
mutation occurred during this addendum.
