# ADMIN-EVENT-ACTIVATION — Enable Admin Event Management and verify Production

- **Status:** DONE — PRODUCTION WRITE ACCEPTANCE PASS / DRAFT RETAINED
- **Priority / track:** P0 product-release / events
- **Owner decision:** 2026-10-11
- **Dependencies:** `EVENT-FLAG-SPLIT`; existing Admin RBAC and canonical Event APIs

## Objective

Enable only the Production Admin Event Management surface, keep the public live Event experience
OFF, verify the resulting frontend and existing read/security boundaries without mutating Event
data, and stop before the first Production write.

## Authorization boundary

The owner authorized adding exactly `VITE_ADMIN_EVENTS_ENABLED=true` to the Vercel Production
environment and rebuilding the current source. `VITE_PUBLIC_EVENTS_ENABLED` must remain absent/OFF
and `VITE_EVENTS_LAUNCH_ENABLED` remains ignored. This task does not authorize Event create, edit,
status transition, upload, replacement, delete, database/Storage writes or any unrelated provider
change.

The owner added a newer bounded approval on 2026-10-11 for exactly one synthetic DRAFT and the
Create -> reload -> cover upload/replace -> Edit -> stale-version conflict sequence. That approval
supersedes the write prohibition only for those steps. Publish, status transition, delete/cleanup,
public activation and unrelated Production changes remain unauthorized.

## Activation evidence — 2026-10-11

| Gate               | Result                                                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Git / source       | `HEAD == origin/main == b3799669cf5fdb463cf03629e05b4b98fefe1f0a`; existing local evidence docs preserved               |
| Preflight flags    | Admin/public/legacy keys were absent; strict source resolver and prior ON/OFF matrix reused                             |
| Preflight frontend | Production served `index-XtzcBb4D.js` from the READY `b379966` deployment                                               |
| Preflight API      | `/api/health/live` and `/api/health/ready` returned 200; database/Redis `ok`, email/Storage `configured`                |
| Vercel change      | Added one Config variable, `VITE_ADMIN_EVENTS_ENABLED=true`, scoped only to Production                                  |
| Public / legacy    | `VITE_PUBLIC_EVENTS_ENABLED` remains absent/OFF; legacy key remains absent and ignored                                  |
| Deployment         | `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4` READY, Production, source `b379966`                                                  |
| Live bundle        | `index-CrsPaw6k.js`, 919,216 bytes; Admin list/create/metrics markers present; slider endpoint and legacy marker absent |
| Rollback           | Previous `dpl_GGJ7ZaVioxoNt3nLcsMd7XHY8y36` and other READY Production deployments remain available                     |
| Render             | No backend change or restart; live/readiness pass and accepted `e2ef4c0` / `d15cb1d` baseline remains controlling       |

## Read-only Production smoke

| Surface             | Result                                                                                                |
| ------------------- | ----------------------------------------------------------------------------------------------------- |
| Public desktop      | Five static titles present; no Event links; no horizontal overflow                                    |
| Public mobile       | 390 x 844: five static titles present, mobile navigation active, no horizontal overflow               |
| Public network      | Zero `/event-sliders` resource requests; public dynamic detail/navigation remains OFF                 |
| Browser console     | Zero warning/error entries on the new-bundle Landing smoke                                            |
| Existing USER       | Profile and Buddy Matching render; direct `/admin/events` returns to public Landing with no Admin UI  |
| Anonymous           | Direct `/admin/events` redirects to `/adminLogin`; backend Admin list returns 401 with `no-store`     |
| Authenticated ADMIN | PASS: Dashboard/Events nav, empty `0–0 of 0`, Create form, Edit not-found boundary and metrics render |
| Event writes        | Zero; no POST/PUT/PATCH/DELETE, upload, Event/account/database/Storage mutation or publication        |

The deployed artifact proves that Admin list/create/metrics code is compiled while the public slider
is not. Authenticated read-only verification confirms the Event navigation, complete list/filter
shell, authoritative empty inventory, localized Create DRAFT form and safe Edit not-found boundary.
Dashboard Published/Upcoming Event metric cards render `Not available`; they were not interpreted as
zero. The Admin list, Create and Edit-boundary pages recorded zero browser warning/error entries.
Because Production has no Event rows, a populated edit form is not applicable until the separately
approved synthetic DRAFT exists.

## Prepared Production write acceptance — authorization consumed

The proposed synthetic record is clearly named
`[PROD ACCEPTANCE — DRAFT] Admin Event Management Test 2026-10-11`, with an equivalent German test
title, test-only EN/DE descriptions and locations, `Asia/Ho_Chi_Minh`, `MEMBERS` visibility,
registration disabled and status fixed at `DRAFT`. A neutral non-sensitive JPEG/PNG/WebP under the
5 MiB limit would be used as the cover. The record must never be published or reused as real
content.

Planned scenarios after separate approval:

1. `POST /api/admin/events` creates the synthetic DRAFT and an atomic audit log.
2. `GET /api/admin/events/{id}` plus a page reload proves persistence.
3. `POST /api/admin/events/{id}/media` writes cover metadata and one private `event-media` object,
   records the audit entry and returns the next Event version.
4. `PUT /api/admin/events/{id}` changes only test metadata using the current optimistic version.
5. A second cover upload replaces the cover, writes new metadata/object and attempts cleanup of the
   previous private object; any `cleanup_pending` response is treated as a stop condition.
6. A deliberately stale version is submitted only if separately approved as part of the write
   test; the expected result is 409 with no accepted content change.
7. Reload and read-only USER/Anonymous checks prove the Event remains DRAFT and is not discoverable
   through public surfaces. `PATCH .../status` is not used to publish.

Expected side effects are one persistent Event row, Event-media row(s), audit-log rows, incremented
Event versions and private Storage object writes. The endpoints contain no email/notification
operation, but the acceptance must still observe that none is emitted. Failure risks are a retained
test Draft, an orphaned/replaced object when cleanup fails, stale-version conflicts and accidental
status/visibility mistakes. Cleanup is intentionally not part of the first approval: retain the
DRAFT and object identities for a later explicit delete/cleanup authorization, or approve those
deletes separately after evidence capture.

## Production write acceptance execution — PASS 2026-10-11

| Scenario               | Result                                                                                                      |
| ---------------------- | ----------------------------------------------------------------------------------------------------------- |
| Create                 | 201; Event `132dfbb1-b966-4cd0-a02e-901cd50cc8f5`; version 1; DRAFT/MEMBERS/registration OFF                |
| Save / reload          | Authenticated detail GET 200; the same ID and version 1 persisted                                           |
| Cover upload           | Media `9f00a563-24d7-48d5-87ac-33c77abf5c9c`; object `0b9f13bd-ab39-4563-b835-eaea8d6067fe.webp`; version 3 |
| Cover replacement      | Media `e3f58e3f-f1d4-44aa-839c-c7f699602215`; object `b566eab7-7807-4c2b-a99f-dd898e1dfe7d.webp`; version 5 |
| Replacement cleanup    | Both responses `cleanup_pending=false`; old A object automatically removed; active B object retained        |
| Edit                   | Organizer changed to the synthetic edited marker; version 6                                                 |
| Version conflict       | Stale version 5 returned 409 with reload/review UI; accepted row and audit count unchanged                  |
| Public detail / slider | EN/DE detail 404; EN/DE slider `[]`; no Landing synthetic title, link or slider request                     |
| Final state            | DRAFT, MEMBERS, registration OFF, `published_at=NULL`, active cover B, no manual delete                     |
| Audit / email          | Six expected audit rows; zero Event-related transactional outbox rows                                       |
| Health / console       | live/ready 200; dependencies healthy/configured; zero Admin/conflict/Landing warning/error                  |

The first cover metadata/object was removed by the backend as the normal atomic replacement cleanup;
the agent did not call a delete endpoint or perform manual cleanup. The active private object and
synthetic DRAFT remain intentionally retained. No real Event or user row was changed. Source code,
deployments, provider configuration and `VITE_PUBLIC_EVENTS_ENABLED` were unchanged.

Detailed evidence:
[`admin-event-production-write-acceptance-2026-10-11.md`](../../operations/admin-event-production-write-acceptance-2026-10-11.md).

## Continuation gate

Production write acceptance is complete. Stop before every publish/status change, new upload,
delete/cleanup or public activation. A future cleanup must identify the retained Event and active
object explicitly and requires separate owner approval.
