# EVENT-OPTIONAL-PUBLISH-001 — Optional Event schedule and User registration action

**Status:** DONE — COMMIT/PUSH APPROVED / NOT DEPLOYED
**Priority:** P0
**Track:** events
**Assigned:** 2026-10-14

## Objective

Allow announcement-only Events to be published without locations or start/end timestamps, simplify
the Admin Event Details inputs, and make an enabled HTTPS registration URL visible to authorized
Users through the public/member Event projection.

## Scope

- Keep English/German titles, English/German descriptions, and a ready cover as publish blockers.
- Make both localized locations and both schedule timestamps optional through form, service and
  public response contracts; never synthesize missing values.
- Remove Category, Organizer, Audience and Maximum participants from the Admin form while retaining
  stored values on edits and keeping the registration-enabled control plus HTTPS URL.
- Render registration actions only when the visible Event projection has both
  `registration_enabled=true` and a valid persisted URL.
- Preserve DRAFT, visibility, deleted/cancelled and role boundaries.
- Do not add a destructive migration or change Production data/configuration.

## Unscheduled public policy

An unscheduled published Event is an announcement. It remains available through the same public or
member visibility rules as a scheduled Event and is eligible for the Slider when cover-ready.
Scheduled upcoming Events sort first by start date; announcements with no start date sort after
them. Missing schedule/location facts are omitted from Event Detail instead of formatted as fake or
invalid values. Phase filters continue to exclude Events that cannot derive a phase.

## Acceptance criteria

1. Scheduled and announcement-only Events can publish; required localized content and cover remain
   enforced.
2. Partial location/schedule data serializes and renders safely in EN and DE.
3. The four removed Admin fields are absent and existing stored values are not overwritten.
4. HTTPS registration URL persists and appears for an authorized User only when registration is
   enabled; disabled, missing, unsafe and unauthorized cases remain protected.
5. Focused backend/frontend tests, relevant full suites, typecheck, lint, formatting and builds pass.
6. No push, deployment, Production write, feature-flag change or unrelated cleanup occurs under
   this implementation task.

## Completion evidence

- Event database columns and the start/end ordering constraint already accept null/partial values;
  no migration is required.
- The Admin request and backend persistence already map `registration_url` and
  `registration_enabled` consistently.
- The confirmed visibility defect is downstream: User Dashboard does not request/render Event
  registration data, and Event Detail also omits the returned registration fields.
- Backend publication now requires only localized titles/descriptions and a ready cover; supplied
  schedules still enforce ordering/deadline rules. Public responses accept null dates, phase and
  location. Slider eligibility includes future scheduled Events followed by start-date-free
  announcements with deterministic nulls-last ordering.
- Admin hides Category, Organizer, Audience and Maximum participants, but retains their loaded
  values in the update payload. Registration enabled plus its HTTPS URL remain editable.
- User Dashboard fetches the audience-safe Event list with viewer credentials and renders exact
  persisted registration links only for enabled registration. Event Detail uses the same rule;
  cancelled/disabled/missing URL states render no action. Query invalidation under `['events']`
  refreshes changed URLs.
- Focused verification: backend 38 PASS; frontend 6 files / 32 PASS.
- Full verification: backend 1,413 PASS / 37 explicit live-environment SKIP; frontend 86 files /
  799 PASS; Ruff, mypy (107 files), TypeScript, ESLint and Prettier PASS.
- Production-target frontend build with Admin ON/Public ON PASS; only the existing chunk-size
  advisory remains. Testing Library renders cover EN/DE and 390 px registration behavior.
- No migration, Production write/configuration change, commit, push or deployment occurred.

## Release boundary

The owner approved a direct-to-main commit and push from verified base
`9df8c64493c3273f32e68f7193fb6b9ad70ec89d`. The resulting commit identifier is reported after Git
creates it. Production deployment and any Production feature/configuration action remain separately
gated.
