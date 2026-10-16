# FE-EVENT-DETAIL-TEMPLATE-001

**Control-plane status:** DONE — PRODUCTION VERIFIED
**Track:** events
**Priority:** P0 product-release
**Assigned:** 2026-10-14
**Dependencies:** `FE-031`, `FE-014B`, `EVENT-FLAG-SPLIT`, `ADMIN-EVENT-ACTIVATION`

## Objective

Diagnose why the Admin-published Event is not visible to Users, refine the existing reusable Event
detail template, and reduce each live Landing Slider card to its cover plus title without creating a
second Event content source.

## Verified Production diagnosis — read only

- Production Admin inventory contains the retained synthetic DRAFT and one real Event,
  `0a9fe1f9-ea26-4426-bfd8-8900113de46f`, titled
  `𝐅𝐈𝐄𝐋𝐃 𝐓𝐑𝐈𝐏 𝐓𝐎 𝐊𝐀𝐖𝐀𝐙𝐎 𝐂𝐑𝐀𝐅𝐓 𝐕𝐈𝐋𝐋𝐀𝐆𝐄`.
- The real Event is `PUBLISHED`, `PUBLIC`, has a ready active cover and complete EN/DE content, but
  its 2026-10-10 schedule computes as `COMPLETED` on 2026-10-14.
- Anonymous detail reads return 200 in EN and DE. Slider reads return `200 []` because the canonical
  slider projection requires `start_date >= now()` in addition to publication, public visibility,
  non-deletion and a ready active `EVENT_COVER`.
- Production serves frontend bundle `index-CrsPaw6k.js`: Admin Events are enabled, while
  `VITE_PUBLIC_EVENTS_ENABLED` remains OFF. The Landing therefore uses the five static posters and
  `/events/:eventId` remains behind the normal public 404 boundary.
- No Production write, flag/configuration change or deployment occurred during diagnosis.

## Reused architecture and contract

- Route: `/events/:eventId`, gated in the frontend by `VITE_PUBLIC_EVENTS_ENABLED`.
- Canonical read: `GET /api/events/:eventId?locale=en|de` through `publicEventsClient` and
  `usePublicEvent`; no duplicate Description field, page table or per-Event component.
- The Admin Description is plain text (maximum 10,000 characters). React text rendering plus
  `white-space: pre-wrap` preserves line/paragraph breaks and escapes HTML. Rich text is not
  supported and unsafe raw HTML is not introduced.
- Backend visibility remains authoritative and independent of the frontend flag. Anonymous detail
  requires a non-deleted, published `PUBLIC` Event; verified active Users may also read eligible
  `MEMBERS` Events. Published or cancelled Events remain readable after completion, while the
  Landing Slider is upcoming-only.

## Implementation

- Refined the existing detail page into a responsive legacy-inspired article: contained hero cover,
  strong title/phase hierarchy, prominent Description, public metadata, loading/error/not-found/
  cancelled states and a clear Back-to-home action.
- Kept the existing Event query, direct-route behavior, localization and signed-cover refresh.
- Reduced each Slider card to cover plus title; the whole canonical card remains a keyboard-focusable
  link. Description, date, location and visible CTA copy were removed from cards.
- Added a non-broken-image fallback that recovers when a refreshed signed cover URL is supplied.

## Controlled Kawazo acceptance — 2026-10-14

- After explicit owner confirmation, only Kawazo `start_date` and `end_date` were changed from
  2026-10-10 to 2026-11-10 while preserving 07:20–19:00 Asia/Ho_Chi_Minh and the 11h40m duration.
- The Event advanced from version 3 to 4 and its derived phase became `UPCOMING`. `PUBLISHED`,
  `PUBLIC`, localized content, cover, registration configuration/deadline, timezone and
  `published_at` remained unchanged.
- Fresh public EN/DE reads returned the updated canonical Event. The Slider returned exactly Kawazo;
  the retained synthetic DRAFT remained excluded and returned the public 404 boundary.
- The public frontend flag stayed OFF. No Event publication, deletion, media/user change, deployment
  or push occurred.

## Acceptance evidence

- Focused frontend Admin/Slider/Detail/Auth regression: 8 files / 62 tests PASS.
- Full frontend: 85 files / 791 tests PASS.
- TypeScript, ESLint and Prettier: PASS.
- Normal and public/admin-enabled production builds: PASS; existing large-chunk advisory only.
- Focused backend Event suite on CPython 3.12.10: 112 PASS / 1 explicit live-database SKIP.
- Local browser acceptance against read-only Production Kawazo APIs: the live card contained only
  cover/title, linked to the matching UUID, rendered exact EN/DE Description after click and direct
  reload, loaded its 1448 x 2048 image, produced no horizontal overflow at desktop or 390 x 844, and
  recorded zero console warning/error.
- Direct reload exposed and fixed a session-bootstrap regression: a second private-query cleanup
  after anonymous 401 recovery could cancel the newly enabled detail query. An integration test now
  covers that boundary.
- The complete isolated Admin -> publish -> Slider -> Detail mutation workflow remains covered by
  the preserved 2026-10-10 acceptance (79 API assertions plus real-browser acceptance). It was not
  repeated because backend/Admin persistence code did not change; the new canonical Description
  refresh behavior is covered by the focused frontend test and artifact-browser acceptance.

Detailed evidence and release proposal:
[`event-detail-template-local-verification-2026-10-14.md`](../../operations/event-detail-template-local-verification-2026-10-14.md)
and
[`event-kawazo-production-release-preflight-2026-10-14.md`](../../operations/event-kawazo-production-release-preflight-2026-10-14.md).

## Release boundary

The verified frontend release commit is
`9df8c64493c3273f32e68f7193fb6b9ad70ec89d`, one local commit ahead of `origin/main`. Kawazo is now
truthfully scheduled as an upcoming `PUBLISHED`/`PUBLIC` Event with a ready cover. Production public
activation still needs a separate explicit approval, a push/deployment of that exact commit and a
frontend rebuild with `VITE_PUBLIC_EVENTS_ENABLED=true`. No backend deployment or migration is
required. Rollback is the retained READY Admin-ON/public-OFF Vercel deployment
`dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4`.

## Controlled release attempt and rollback — 2026-10-14

- Exact commit `9df8c64493c3273f32e68f7193fb6b9ad70ec89d` was pushed without amendment;
  `origin/main` advanced from direct parent `b3799669cf5fdb463cf03629e05b4b98fefe1f0a` to that SHA.
  The commit contains only the seven approved frontend files; the pre-existing documentation and
  local Supabase metadata remained unstaged and outside the push.
- GitHub Actions run `38551287304` completed both required jobs, `CI / Frontend` and
  `CI / Backend`, successfully for the exact approved SHA.
- Vercel automatic deployment `dpl_ArkWFd8NjyVF4GeiQ1h4ANbMarzu` was an intermediate
  Public-OFF artifact. After CI passed, Production Config was changed to
  `VITE_PUBLIC_EVENTS_ENABLED=true` while `VITE_ADMIN_EVENTS_ENABLED=true` was preserved, and
  deployment `dpl_7jRJsyD4AqJtFMKMEUHx72Fpba8K` rebuilt the exact approved SHA.
- Pre-smoke anonymous Slider reads returned exactly Kawazo in EN and DE. Anonymous/User Slider,
  EN/DE detail, click/direct navigation/reload, normal-User boundary, Admin Event Management,
  desktop/mobile layout, homepage unaffected sections and console/network health passed.
- Mandatory content consistency failed. The live Kawazo poster showed `EVENT DATE 10/10/2026` and
  `7:40–16:30`, while the canonical Event detail showed November 10, 2026 and 07:20–19:00. This is
  independent of the accepted registration-deadline condition and makes the public presentation
  materially contradictory.
- Rollout stopped immediately. No Event, registration, cover, Storage object, user, backend,
  database, schema or DNS data was changed. Retained deployment
  `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4` was promoted; Production now serves its Admin-ON/public-OFF
  `b379966` artifact `index-CrsPaw6k.js`. The public Config was reset to exact `false` for future
  builds and the Admin Config remains exact `true`.
- Post-rollback verification returned HTML/bundle 200, found no public Slider/detail route marker,
  rendered the static five-poster carousel with zero Event links, restored the public Event route
  404 boundary, and loaded the two-row Admin Event inventory with zero browser warning/error.

Status: **RELEASE ROLLED BACK — CONTENT CORRECTION REQUIRED**. The approved frontend commit remains
on `origin/main`, but the Production aliases serve the verified rollback artifact. A future release
requires explicit authorization to reconcile the Kawazo cover with the canonical schedule, fresh
read-only eligibility/content verification, and a new controlled public activation. Do not modify
the Event or cover under this completed release authorization.

## Final owner-accepted release — 2026-10-14

This section supersedes the rollback requirement above. The owner explicitly accepted the poster
versus canonical date/time discrepancy as an out-of-scope content issue and directed that it must
not cause another rollback or Event/cover/registration mutation.

| Gate                             | Result                                                                                                                 |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Exact release source             | `main=origin/main=9df8c64493c3273f32e68f7193fb6b9ad70ec89d`; direct parent `b379966`; seven intended frontend files    |
| New source commit / push         | None; the approved commit already existed on remote `main`                                                             |
| Fresh focused / full frontend    | 8 files / 90 tests PASS; 85 files / 791 tests PASS                                                                     |
| TypeScript / ESLint / Prettier   | PASS / PASS / PASS                                                                                                     |
| Production-target builds         | Admin-ON/public-OFF PASS; Admin-ON/public-ON PASS; existing large-chunk advisory only                                  |
| Required exact-SHA CI            | GitHub run `38551287304`; `CI / Frontend` PASS; `CI / Backend` PASS                                                    |
| Production deployment            | `dpl_48YExmcZG4YREaUGGUmePsaZ9NP2`; Ready; Production; exact SHA; `www.vgubuddyprogram.com`                            |
| Effective build configuration    | `VITE_PUBLIC_EVENTS_ENABLED=true`; `VITE_ADMIN_EVENTS_ENABLED=true`                                                    |
| Serving artifact                 | HTML/bundle 200; `index-kimW3TwX.js`; public and Admin Event markers present; old static Event titles absent           |
| Public eligibility               | Anonymous EN/DE APIs 200 with exactly Kawazo; retained DRAFT absent; Kawazo detail 200; retained DRAFT detail 404      |
| Browser smoke                    | EN/DE Slider/detail, card navigation, direct refresh, User/Admin boundaries, desktop/390 x 844 and console health PASS |
| Runtime health                   | live/ready 200; readiness `ready`; database/Redis `ok`; email/Storage `configured`                                     |
| Homepage regression              | About/Features/Community and existing backgrounds/navigation remain usable; no horizontal overflow                     |
| Rollback baseline                | `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4` retained; source `b379966`; Admin ON/public OFF                                     |
| Production data/backend mutation | None during final release; no Event, registration, media, user, backend, schema or DNS change                          |
| Documentation validation         | Prettier/diff-check PASS; task/index 218/218; 252 Markdown files and 0 broken local links; staging empty               |
| Accepted limitation              | Poster embedded schedule differs from canonical Event data; owner-accepted, out of scope, not a rollback trigger       |
| Audit evidence limitation        | Transactional implementation/tests preserved; specific Production audit row not independently retrieved                |

Result: **PASS — COMMITTED, DEPLOYED, AND PRODUCTION-VERIFIED**. Here “committed” refers to the
preserved approved commit already on `origin/main`; no redundant commit was created.
