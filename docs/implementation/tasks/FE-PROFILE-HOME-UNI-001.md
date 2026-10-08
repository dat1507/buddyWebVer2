# FE-PROFILE-HOME-UNI-001 — Home University User Profile UI

**Feature group:** Profile
**Priority:** Phase 2 Priority 2
**Status:** IMPLEMENTED — AUTOMATED PASS / MANUAL VISUAL GATE OPEN
**Dependencies:** Existing authenticated Profile read/update contract and Profile UI.

- **Objective:** display and edit the existing optional `home_university` value in User Profile.
- **Scope:** own-profile detail, edit-only input, trim/empty-to-null behavior, 200-character client
  validation, save/reload persistence and EN/DE copy.
- **Out of scope:** onboarding/registration requirement, directory/autocomplete, public candidate
  exposure, matching/recommendation changes, browser storage, backend or database work.
- **Relevant modules:** Profile parser/update type, identity edit form, own-profile page, locales and
  focused tests.
- **Frontend changes:** optional edit field and own-profile detail.
- **Backend changes:** none; existing API response/update field is reused.
- **Database changes:** none; existing column is reused.
- **Security:** authenticated own-profile/Admin visibility only; render as inert text.
- **Acceptance:** saved value survives reload, empty clears to null, over-limit input is rejected,
  other Profile fields remain stable, and no matching code changes.
- **Tests:** Profile view/edit tests, persistence payload, max-length/empty behavior, EN/DE,
  TypeScript, ESLint, Prettier, build and local browser verification.
- **Complexity:** S.
- **Production impact:** existing authenticated Profile update only after separate release approval.
- **Manual actions:** owner reviews local Profile UI and separately approves any Production push.

## Implementation evidence — 2026-10-08

- The own-profile page now displays `home_university`; the existing identity editor exposes it only
  in edit mode, not onboarding or registration.
- Save trims the value, sends whitespace-only input as `null`, enforces the existing 200-character
  limit and includes EN/DE labels and guidance. No browser-storage fallback was added.
- The existing authenticated Profile response/update field is reused. No API, database, migration,
  matching or recommendation file changed, and the field remains absent from matching inputs.
- Focused tests cover display, persistence payload/reload state, clearing, length rejection, EN/DE
  and onboarding exclusion. Lint, typecheck, formatting and production build pass.
- Authenticated desktop/mobile visual inspection remains an explicit manual gate; no safe local
  authenticated browser session was available and the computer-use browsers could not reach the
  terminal-local Vite server. No Production account or endpoint was used for this verification.
