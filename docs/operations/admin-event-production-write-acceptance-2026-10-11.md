# Admin Event Production write acceptance — 2026-10-11

## Scope and authorization

The owner authorized exactly one isolated synthetic Production Event and the following sequence:

`Create -> Save/Reload -> Cover Upload/Replace -> Edit -> Version Conflict`

The Event had to remain `DRAFT`, `MEMBERS`, with registration OFF. Publish, cancel, delete, manual
cleanup, real-Event/user mutation and `VITE_PUBLIC_EVENTS_ENABLED` were outside the approval.

## Retained acceptance record

| Field               | Final value                                                        |
| ------------------- | ------------------------------------------------------------------ |
| Event ID            | `132dfbb1-b966-4cd0-a02e-901cd50cc8f5`                             |
| English title       | `[PROD ACCEPTANCE — DRAFT] Admin Event Management Test 2026-10-11` |
| Status / visibility | `DRAFT` / `MEMBERS`                                                |
| Registration        | OFF; URL/deadline/capacity unset                                   |
| Schedule            | Unset; timezone `Asia/Ho_Chi_Minh`                                 |
| Version             | 6                                                                  |
| Published           | `published_at=NULL`                                                |
| Active cover media  | `e3f58e3f-f1d4-44aa-839c-c7f699602215`                             |
| Active object       | `event-media/b566eab7-7807-4c2b-a99f-dd898e1dfe7d.webp`            |
| Active object shape | WebP; 47,176 bytes; 1,520 x 450; `READY`                           |

## Scenario evidence

1. Create returned 201 and version 1. The Admin edit route opened for the same UUID.
2. Reload issued authenticated detail GET 200 and restored the same DRAFT fields/version.
3. Cover A upload advanced version 2 -> 3 and returned:
   - media `9f00a563-24d7-48d5-87ac-33c77abf5c9c`;
   - object `event-media/0b9f13bd-ab39-4563-b835-eaea8d6067fe.webp`;
   - WebP, 43,248 bytes, 720 x 960, `READY`;
   - `cleanup_pending=false`.
4. Cover B replacement advanced version 4 -> 5 and returned:
   - media `e3f58e3f-f1d4-44aa-839c-c7f699602215`;
   - object `event-media/b566eab7-7807-4c2b-a99f-dd898e1dfe7d.webp`;
   - WebP, 47,176 bytes, 1,520 x 450, `READY`;
   - `cleanup_pending=false`.
5. The replacement path automatically removed cover A metadata and Storage object after commit.
   The agent did not call any delete endpoint or perform manual cleanup. Direct Storage verification
   found only the retained B object.
6. The accepted content Edit changed only the synthetic organizer marker and advanced version 5 -> 6.
7. A second tab kept version 5, changed only a test field locally, and submitted it after version 6
   existed. The API returned 409 and the UI displayed the reload/review recovery message. Database
   state stayed at version 6; the attempted conflict marker was not persisted.

## Audit and side-effect evidence

The Event has exactly six expected audit rows:

- one `event.create` at version 1;
- three accepted `event.update` entries producing versions 2, 4 and 6;
- two `event.media_replace` entries producing versions 3 and 5.

The rejected stale request created no audit row. Event-related transactional outbox rows are zero,
so the acceptance emitted no Event email/notification work.

No real Event existed in the Admin inventory before the acceptance. The final inventory is `1–1 of
1` and contains only this clearly labeled synthetic DRAFT. No user data, source code, runtime config,
deployment, DNS, secret or provider setting changed.

## Public exclusion and runtime health

- Anonymous `GET /api/events/{id}?locale=en|de`: 404 `Event not found`.
- Anonymous `GET /api/event-sliders?locale=en|de`: 200 with `[]`.
- Production Landing: no synthetic title, Event ID or Event link; zero `/event-sliders` resource
  requests; static five-item carousel remains active.
- Admin, stale-conflict and public Landing console warning/error entries: zero.
- API live: 200 `alive`.
- API readiness: 200 `ready`; database/Redis `ok`; email/Storage `configured`.
- `VITE_ADMIN_EVENTS_ENABLED` remains ON. `VITE_PUBLIC_EVENTS_ENABLED` remains absent/OFF and the
  legacy flag remains ignored.

## Result and stop boundary

**PASS — PRODUCTION WRITE ACCEPTANCE COMPLETE / DRAFT RETAINED.**

Do not publish, cancel, upload again, delete/cleanup the Event or active object, or enable public live
Events without a new explicit owner approval. A future cleanup must target the Event and active
object recorded above; the already replaced A object no longer exists.

No full regression was rerun because no source/config change occurred. Documentation validation
passed Prettier, `git diff --check`, task/index 217/217, 253 Markdown files with zero broken local
links, zero high-confidence secret hits, zero tracked source/runtime changes and an unchanged legacy
archive.
