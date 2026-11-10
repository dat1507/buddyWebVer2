# Kawazo Slider visibility after an End Date edit

## Read-only Production observation — 2026-11-10

The public Events list returned the current Kawazo Event as PUBLISHED and ONGOING, with
Start Date 2026-11-09 07:00 and End Date 2027-12-12 07:00 in Asia/Ho_Chi_Minh
(00:00 UTC on the same dates). The EN and DE Slider endpoints returned HTTP 200 with empty
arrays and Cache-Control no-store. The historical October record ID returned 404. The current
record was identified by its public title. The earlier reported disappearance time and the
Production attempt to clear End Date were not observed.

## Cause and existing rules

- [Slider projection](../../../apps/api/app/services/event_sliders.py) requires PUBLISHED status,
  a publication timestamp, an undeleted Event and a ready, undeleted cover owned by that Event.
  Its schedule filter is Start Date at or after the UTC reference instant, or no Start Date.
  The legacy audience field is not a predicate. The query returns up to 12, ordered by Start Date
  with nulls last and an ID tiebreaker. Landing and User Events show the first five.
- The [upcoming-only contract](../../implementation/tasks/FE-EVENT-DETAIL-TEMPLATE-001.md) and
  [announcement contract](../../implementation/tasks/EVENT-OPTIONAL-PUBLISH-001.md) explain why
  extending or clearing End Date cannot make a past-start Event eligible. With a complete
  schedule, phase is derived at read time. A missing date leaves phase unset. There is no
  archived or expired editorial state. A past End Date alone is not a Slider predicate, so
  an end-only announcement with a null Start Date is still eligible under the current query.
- The [Admin form](../../../apps/web/src/features/admin-events/event-form.ts) converts times
  in the Event's selected timezone and sends explicit null for a cleared End Date. The
  [service](../../../apps/api/app/services/events.py) distinguishes null from omitted fields,
  validates schedules, and preserves Start Date when omitted. Publishing an already published
  Event leaves its editorial state and publication history intact. PostgreSQL stores both
  dates as nullable timezone-aware instants. Repository migrations show no expiration job or
  visibility trigger. Production database internals and authenticated Admin were not inspected.
- The [Landing selection](../../../apps/web/src/features/events/event-slider.ts) only slices the
  API response. Admin mutations invalidate the Slider query in the same client and the existing
  query refetches every 60 seconds. Neither a browser timezone conversion nor stale browser data
  accounts for the observed empty API response.

## Local reproduction and scope

Against disposable PostgreSQL 17, the Admin create, update, read and status HTTP handlers and the
public Slider HTTP handler reproduced the behavior with synthetic data. Authentication, CSRF and
cover signing used fixtures. The published Event appeared before its Start Date, disappeared after
that instant and was already absent one microsecond before 07:00 UTC+7 at the original End Date.
It stayed absent at that boundary. Save + Publish persisted a 2027 End Date and, on the next edit,
persisted null. The record stayed absent in EN and DE. A future Start Date restored it while keeping
End Date null. Draft and cancelled records remained hidden. Existing coverage checks other eligible
Events, order, limits and localization.

Added two regression cases to test_events.py for explicit null and a UTC+7 extension followed by
Publish. Runtime behavior remains under the upcoming-only contract. Showing ongoing Events would
require an explicit eligibility decision covering both Landing and User Events, including what a
past Start Date with no End Date means. A truthful reschedule with a future Start Date is already
supported. No migration or manual database correction is required.

## Verification

- Backend focused suites: 31 passed. Ruff lint passed. The Ruff format check flags the same
  pre-existing long function signature on the baseline and working copy. The added test is formatted.
- Frontend focused suites: 51 passed. The feature-enabled integration suite passed all 10 cases
  on retry after a temporary-file failure. Focused ESLint and Prettier passed. The TypeScript
  and production build passed with the existing large-chunk advisory.
- Local Chrome used the actual PostgreSQL-backed HTTP response as a fixture. At 1440 px in EN
  and 390 px in DE, the card linked to Event Detail when returned, the empty state rendered
  when absent, and neither case overflowed. Authenticated browser CRUD was not exercised.
