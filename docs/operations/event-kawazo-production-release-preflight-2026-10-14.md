# Kawazo Production acceptance and public-release preflight — 2026-10-14

## Authorized boundary

The owner authorized one Production content change only: move the real Kawazo Event schedule to
2026-11-10 while preserving its local time and duration. The authorization did not include
publication changes, deletion, media changes, edits to any other Event or user data, public-flag
activation, deployment or push.

## Release-candidate baseline

| Check                       | Verified result                                                                           |
| --------------------------- | ----------------------------------------------------------------------------------------- |
| Remote application baseline | `origin/main` was `b3799669cf5fdb463cf03629e05b4b98fefe1f0a`                              |
| Current Production frontend | Vercel deployment `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4`, READY/current, built from `b379966` |
| Rollback frontend           | `dpl_GGJ7ZaVioxoNt3nLcsMd7XHY8y36`, READY, public/admin OFF artifact                      |
| Admin flag                  | `VITE_ADMIN_EVENTS_ENABLED=true`                                                          |
| Public flag                 | `VITE_PUBLIC_EVENTS_ENABLED` absent/OFF                                                   |
| Legacy flag                 | `VITE_EVENTS_LAUNCH_ENABLED` absent and ignored by current source                         |
| Deployment/config mutation  | None                                                                                      |

The public switch is a Vite build-time value. Enabling it later requires a frontend rebuild; a
runtime toggle of the currently deployed bundle cannot expose the public Event surfaces.

## Kawazo write acceptance

Event ID: `0a9fe1f9-ea26-4426-bfd8-8900113de46f`.

| Field          | Before                 | After                  |
| -------------- | ---------------------- | ---------------------- |
| `start_date`   | `2026-10-10T00:20:00Z` | `2026-11-10T00:20:00Z` |
| `end_date`     | `2026-10-10T12:00:00Z` | `2026-11-10T12:00:00Z` |
| Local schedule | 2026-10-10 07:20–19:00 | 2026-11-10 07:20–19:00 |
| `phase`        | `COMPLETED`            | `UPCOMING` (derived)   |
| `version`      | 3                      | 4                      |

The accepted update request contained only `version`, `start_date` and `end_date`. A fresh Admin
read showed that only `start_date`, `end_date`, derived `phase`, `version` and `updated_at` changed.
Status remained `PUBLISHED`; visibility remained `PUBLIC`; timezone, localized content, cover,
registration URL/state/deadline and `published_at` remained unchanged. The cover was not uploaded,
replaced or deleted.

The Admin update route records `event.update` in the same database transaction as the Event update;
the 200 response therefore proves that the business write and its audit write committed together.
No audit-log read endpoint or implemented Audit Log UI exists in this release, so an independent
row retrieval was not claimed.

## Production read-only verification after the write

- Anonymous EN and DE detail reads returned 200 with the canonical localized content, the unchanged
  ready cover and the new schedule.
- The EN public Slider returned exactly Kawazo at sort order 0 with the canonical
  `/events/0a9fe1f9-ea26-4426-bfd8-8900113de46f` link.
- A final refreshed Admin inventory showed exactly two Events: Kawazo as
  `PUBLISHED`/`PUBLIC`/`UPCOMING`, and the retained acceptance Event
  `132dfbb1-b966-4cd0-a02e-901cd50cc8f5` as `DRAFT`/`MEMBERS` with no schedule.
- The retained DRAFT remained unavailable through the public detail boundary, and no second Event
  appeared in the public Slider response.
- `VITE_PUBLIC_EVENTS_ENABLED` remained OFF, so the deployed Landing and direct public Event route
  were not activated.

## Release candidate and regression evidence

Local release commit:
`9df8c64493c3273f32e68f7193fb6b9ad70ec89d` (`feat(events): prepare public event detail release`).
It is one local commit ahead of `origin/main`; it has not been pushed or deployed.

The release candidate contains the cover-title Slider, reusable canonical Event detail template and
a focused anonymous-bootstrap fix found during direct-route browser acceptance. The old bootstrap
path cleared private queries twice after a 401, which could cancel a newly enabled anonymous Event
query and leave a direct reload pending. The second clear is now avoided after the already-awaited
bootstrap cleanup, with an integration regression test.

| Gate                                       | Result                                                                |
| ------------------------------------------ | --------------------------------------------------------------------- |
| Focused frontend                           | 8 files / 62 tests PASS                                               |
| Full frontend                              | 85 files / 791 tests PASS                                             |
| TypeScript / ESLint / Prettier             | PASS / PASS / PASS                                                    |
| `git diff --check`                         | PASS                                                                  |
| Admin-ON/public-OFF production build       | PASS                                                                  |
| Admin-ON/public-ON production build        | PASS; existing chunk-size advisory only                               |
| Local browser with Production Kawazo reads | Slider card, click, direct reload, exact EN/DE content and cover PASS |
| Responsive/browser console                 | Desktop and 390 x 844 no overflow; cover decoded; 0 warnings/errors   |
| Visibility boundaries                      | Invalid UUID and retained DRAFT both rendered the public 404 boundary |
| Backend regression                         | Not repeated; no backend, schema, Storage or runtime change           |

## Proposed controlled release — not executed

1. Obtain a new explicit public-release approval.
2. Set Production `VITE_PUBLIC_EVENTS_ENABLED=true` while keeping
   `VITE_ADMIN_EVENTS_ENABLED=true`.
3. Push/deploy exactly commit `9df8c64493c3273f32e68f7193fb6b9ad70ec89d` to the existing Vercel
   frontend project. No backend deploy or migration is required.
4. Verify EN/DE Slider cardinality/content, cover/title-only card, canonical click and direct reload,
   anonymous/User visibility, desktop/mobile layout and console/network health.
5. Stop without changing Kawazo publication state or the retained DRAFT.

Rollback is frontend-only: promote retained READY deployment
`dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4`, which is the current Admin-ON/public-OFF artifact. After the
rollback, remove or reset `VITE_PUBLIC_EVENTS_ENABLED` before any later build. Event rows, media and
backend deployment remain unchanged.

## Safety result

**READY FOR RELEASE APPROVAL — NOT DEPLOYED.** The only Production data change was the authorized
Kawazo schedule update. No public flag, deployment, push, publication, deletion, other Event, user,
database schema, Storage object, DNS or backend/provider state was changed.

## Later controlled release attempt — rolled back

This section supersedes only the proposed-release state above; it preserves the preflight as the
historical decision record.

| Gate                       | Result                                                                                                                            |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Exact push                 | PASS — `origin/main=9df8c64493c3273f32e68f7193fb6b9ad70ec89d`; no amend/new commit                                                |
| Required CI                | PASS — run `38551287304`; `CI / Frontend` and `CI / Backend` passed for the exact SHA                                             |
| Automatic deployment       | `dpl_ArkWFd8NjyVF4GeiQ1h4ANbMarzu`; exact SHA; intermediate Public-OFF artifact                                                   |
| Intended launch deployment | `dpl_7jRJsyD4AqJtFMKMEUHx72Fpba8K`; exact SHA; Public ON/Admin ON artifact                                                        |
| Eligibility                | PASS — EN/DE Slider returned exactly Kawazo immediately before smoke                                                              |
| Functional smoke           | PASS through anonymous/User EN/DE Slider/detail, direct reload, Admin, responsive, console/network and unaffected-homepage checks |
| Content consistency        | **FAIL** — poster said Oct 10, 07:40–16:30; canonical detail said Nov 10, 07:20–19:00                                             |
| Recovery                   | PASS — promoted `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4`; serving bundle `index-CrsPaw6k.js` from `b379966`                             |
| Recovery API               | live 200; readiness 200/`ready`; EN/DE Slider each still exactly Kawazo; retained DRAFT absent                                    |
| Future-build flags         | `VITE_PUBLIC_EVENTS_ENABLED=false`; `VITE_ADMIN_EVENTS_ENABLED=true`                                                              |

The release stopped at the failed mandatory gate. No Production Event, registration setting,
cover/media object, user, backend, database, schema or DNS state was changed. Post-rollback checks
confirmed static five-poster Landing behavior, no public Event links/routes, working Admin Event
Management, HTML/bundle 200 and zero browser warning/error. Vercel labels the older deployment
`Stale` relative to branch freshness, but its page lists the Production current domains and direct
public HTTPS serves its exact bundle.

Final result: **FAIL / SAFELY ROLLED BACK**. Content correction and any later public release require
new explicit approvals.

## Final owner-accepted release

This later record supersedes the rollback requirement above. The owner explicitly accepted the
poster versus canonical schedule mismatch as out of scope and instructed that it not trigger
another rollback. No Event, cover or registration data was changed.

| Gate                          | Result                                                                                                            |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Exact source                  | `origin/main=9df8c64493c3273f32e68f7193fb6b9ad70ec89d`; no amend, new commit or redundant push                    |
| Required CI                   | Run `38551287304`; Frontend PASS; Backend PASS                                                                    |
| Production flags              | `VITE_PUBLIC_EVENTS_ENABLED=true`; `VITE_ADMIN_EVENTS_ENABLED=true`                                               |
| Production deployment         | `dpl_48YExmcZG4YREaUGGUmePsaZ9NP2`; Ready; exact SHA; `www.vgubuddyprogram.com`                                   |
| Serving bundle                | `index-kimW3TwX.js`; 200; dynamic Slider/Admin markers present; old static Event-title markers absent             |
| Final eligibility             | No-cookie EN/DE Slider 200 with exactly Kawazo; retained synthetic DRAFT absent                                   |
| Event boundaries              | Kawazo public detail 200; retained DRAFT public detail 404; invalid ID rejected and 404 UI rendered               |
| Browser functional smoke      | EN/DE Slider/detail, click/reload, normal User/Admin, desktop/mobile, console/network and Landing regression PASS |
| Runtime health                | live/ready 200; readiness `ready`; database/Redis `ok`; email/Storage `configured`                                |
| Retained rollback             | `dpl_ENhaDrJxJfVFMrfPeoKTeoZJ8kd4`, source `b379966`, Admin ON/public OFF                                         |
| Production data/backend delta | None; release changed only frontend build configuration and deployment                                            |

The update/audit transaction evidence remains implementation- and test-based; the specific
Production audit row was not independently retrieved and is not claimed. The registration-deadline
condition remains accepted and was not reinvestigated.

Final result: **PASS — COMMITTED, DEPLOYED, AND PRODUCTION-VERIFIED**.
