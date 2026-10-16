# Event visibility diagnosis and detail-template local verification — 2026-10-14

## Scope and safety boundary

The approved work was read-only against Production and implementation-only in the local repository.
It did not authorize Event mutation, media mutation, public activation, provider configuration,
deployment, push or migration. Production credentials, cookies, tokens and signed media URLs are not
recorded here.

## Production diagnosis

| Check                | Dated result                                                                                            |
| -------------------- | ------------------------------------------------------------------------------------------------------- |
| Admin inventory      | Two records: the retained synthetic DRAFT and real Event `0a9fe1f9-ea26-4426-bfd8-8900113de46f`         |
| Real Event state     | `PUBLISHED`, `PUBLIC`, ready cover, complete EN/DE fields, registration enabled                         |
| Real Event schedule  | 2026-10-10 07:20–19:00 Asia/Ho_Chi_Minh; computed `COMPLETED` on 2026-10-14                             |
| Public Slider API    | EN and DE both 200 with `[]`                                                                            |
| Public detail API    | EN and DE both 200 with the canonical title, Description, schedule, location and cover metadata         |
| Frontend artifact    | `index-CrsPaw6k.js`; Admin Event UI present; live public Slider/detail route absent                     |
| Landing/direct route | Static five-poster Landing; no live Event request/link; direct `/events/<id>` shows normal 404 boundary |
| Runtime health       | API live and readiness both 200                                                                         |
| Production mutation  | None                                                                                                    |

### Root cause

Two independent conditions explain the User-visible absence:

1. The canonical Slider is upcoming-only. Its query requires a non-deleted Event with
   `status=PUBLISHED`, non-null `published_at`, `visibility=PUBLIC`, `start_date >= now()` and a ready
   active `EVENT_COVER`. The real Event is completed, so the API correctly filters it out.
2. `VITE_PUBLIC_EVENTS_ENABLED` is OFF in the deployed frontend. Even an eligible future Event would
   not replace the static Slider or expose the detail route until a rebuilt frontend is deployed with
   that exact flag set to `true`.

This is not a cover-upload, localization, publication-state or public-detail-API failure. The
completed Event remains readable through the authorized anonymous detail API, which intentionally
has no upcoming-only filter.

## Local implementation

| Area                   | Change                                                                                                                                                                                 |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Detail page            | Reused `/events/:eventId` and the canonical detail API; responsive two-column desktop/one-column mobile article; contained cover; prominent Description; metadata and states preserved |
| Description            | Exact plain text from Admin/API, paragraph breaks preserved by `whitespace-pre-wrap`, React-escaped, no raw HTML                                                                       |
| Slider                 | Per-card visible content reduced to cover and title; whole card remains an accessible canonical link                                                                                   |
| Cover failure          | Replaced broken image with an accessible fallback; a changed signed URL retries normally                                                                                               |
| Backend/schema/storage | No change                                                                                                                                                                              |

## Verification actually run

| Gate                                         | Result                                                                                   |
| -------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Targeted Slider/Detail tests                 | 3 files / 18 tests PASS                                                                  |
| Admin + Slider + Detail frontend flow        | 6 files / 37 tests PASS                                                                  |
| Full frontend suite                          | 85 files / 790 tests PASS                                                                |
| TypeScript / ESLint / Prettier               | PASS / PASS / PASS                                                                       |
| Normal production build                      | PASS; existing large-chunk advisory only                                                 |
| Public+Admin enabled production build        | PASS; existing large-chunk advisory only                                                 |
| Local-fixture artifact build                 | PASS; used only for browser acceptance                                                   |
| Focused backend Event suite, CPython 3.12.10 | 112 PASS / 1 SKIP (`EVT003_TEST_DATABASE_URL` opt-in live migration test)                |
| Browser Slider card                          | One canonical fixture; cover/title present; Description/location absent; exact UUID link |
| Browser click/direct reload                  | Correct detail route, exact EN/DE Description after click and direct reload              |
| Browser responsive/image                     | No horizontal overflow at 1521 px desktop or 390 x 844 mobile; cover decoded             |
| Browser console                              | 0 warnings / 0 errors on final artifact flow                                             |

The complete mutation workflow was not recreated. The preserved isolated 2026-10-10 acceptance
already passed 79 API assertions plus real-browser Admin edit, publish, Slider, Detail, EN/DE and
desktop/mobile scenarios. This change does not touch backend/Admin persistence. Current verification
adds exact Description-refresh coverage and final artifact click/reload checks; it does not claim a
new Production write or a newly executed local mutation harness.

## Controlled release proposal — not executed

1. Prepare or truthfully schedule an upcoming Event in Admin; it must be `PUBLISHED`, `PUBLIC`,
   non-deleted, have non-null `published_at`, valid localized content and a ready active cover.
2. Do not change the historical Kawazo schedule solely to force Slider eligibility. Prefer a genuine
   upcoming Event when no correction is needed.
3. Obtain explicit approval to set Production `VITE_PUBLIC_EVENTS_ENABLED=true` and deploy this
   frontend source. Because it is a `VITE_` build-time value, a frontend rebuild/redeployment is
   mandatory.
4. No backend release or database migration is required.
5. After deployment, run a bounded read-only smoke: EN/DE Slider, card cover/title only, click/detail,
   direct reload, anonymous/User policy, desktop/mobile overflow and console/network checks.

Rollback is frontend-only: restore/remove the public flag and redeploy the accepted prior READY
frontend deployment/bundle. The backend and canonical Event rows stay unchanged. Publication,
Event edits, retained-DRAFT cleanup/delete and Production public activation remain separately gated.
