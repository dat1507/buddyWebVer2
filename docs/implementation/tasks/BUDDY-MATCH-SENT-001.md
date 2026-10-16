# BUDDY-MATCH-SENT-001 — Refine Buddy Matching and Sent Invitations

**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED
**Priority:** P1
**Track:** buddy-v2
**Assigned:** 2026-10-16
**Dependencies:** `REC-003`, `REC-004`, `INV-003` through `INV-007`, `BUDDY-001` through
`BUDDY-003`, `PROFILE-V2-001`, `PROFILE-V2-002`

## Objective

Refine the current recommendation-driven Buddy Matching experience so established Buddy pairs are
excluded server-side, recommendation cards show only the requested summary, detailed profile data
is available through an accessible View Profile dialog, and Sent Invitations shows only the
recipient identity and status while preserving all accepted/pending invitation actions and
relationship semantics.

## Scope and sequence

1. Inspect the current recommendation, profile, compatibility, invitation, Match/conversation and
   frontend implementations plus their focused tests and available quality gates.
2. Exclude both participants in every established ACTIVE Match from one another's recommendation
   results without changing pending-invitation behavior, scoring, ordering or pagination.
3. Limit recommendation cards to name, student type, study program and compatibility percentage;
   add an accessible, mobile-safe View Profile dialog for the selected recommendation using the
   existing privacy-safe response and compatibility explanation.
4. Limit Sent Invitations entries to avatar, user name and Accepted/Pending status while preserving
   the accepted explanation, Start chatting destination, removal semantics, confirmation and
   feedback.
5. Run focused backend/frontend tests after each implementation stage, then lint, type checks, the
   full relevant test suites and production build. Record checks as PASS, FAIL or NOT RUN.

## Guardrails

- Reuse the current V2 `Match` relationship and invitation/profile contracts; do not revive the
  superseded batch-matching architecture.
- Do not add a migration unless inspection proves the current schema cannot meet the contract.
- Preserve authentication, authorization, RLS/privacy boundaries, score calculation, eligibility,
  invitation lifecycle, conversation retention and existing navigation.
- Do not mutate Production data, accounts, provider configuration or secrets, and do not push or
  deploy without a separate explicit request.

## Task 0 inspection — complete 2026-10-16

- `GET /api/matching/recommendations` is implemented by `app/api/matching.py`,
  `matching_recommendations.py` and `matching_eligibility.py`. The last service performs the bounded
  server-side candidate query and fixed-count profile/preference projection; it currently applies
  no relationship exclusion. Scores and the five-signal 40/35/15/5/5 explanation are owned by
  `matching_scoring.py` and must remain unchanged.
- The authoritative Buddy relation is `BuddyMatch` in `app_private.matches`. Accepting an invitation
  atomically creates one unordered, unique `ACTIVE` pair and one `BuddyConversation`; either user
  may occupy participant-one or participant-two. A pending invitation creates neither record.
- Recommendation and invitation profile projections already carry avatar, display name, student
  type, major, interests, preferred activities, languages and weekly availability. The canonical
  `StudentProfile` also contains full name, bio, study year, nationality and home university; these
  five fields are not yet in the privacy-allowlisted recommendation DTO.
- `/user/matching` owns recommendation cards and invitation sections. Cards currently render avatar
  plus detailed preferences/availability and compatibility inline. The shared detail renderers are
  `matching-profile-details.tsx`; avatar URLs remain backend-authorized through the matching avatar
  route.
- Sent Invitations is rendered by `SentInvitationCard` in `invitation-sections.tsx`. Accepted rows
  retain `/user/buddy` Start chatting and call the `hide` endpoint; that endpoint only sets
  `sender_hidden_at` on the accepted invitation. It does not update or delete the `ACTIVE` Match,
  conversation or messages. Pending removal uses the existing cancel mutation.
- Focused coverage exists in `test_matching_eligibility.py`,
  `test_matching_recommendations.py`, `test_matching_recommendations_api.py`, invitation read/
  mutation tests, `matching-page.test.tsx`, `matching-page-invitations.test.tsx`, and matching
  contract/client tests. Repository gates are pytest/Ruff/strict mypy for the API and Vitest,
  Prettier, ESLint, TypeScript and the Vite production build for the web app.

No migration, new relationship model or new profile endpoint is required. The existing bounded
recommendation projection can safely carry the five additional allowlisted profile fields for the
selected-profile dialog without an N+1 request.

## Task 1 — complete 2026-10-16

- The bounded candidate query now applies one correlated `NOT EXISTS` predicate against
  authoritative `ACTIVE` Matches. Both participant orientations are covered, so the original
  invitation sender/recipient direction is irrelevant.
- The filter does not read `matching_invitations`; pending invitation behavior, unrelated users,
  eligibility, scoring, ordering, pagination and avatar authorization remain on their existing
  paths.
- Focused Python 3.12 SQL-contract tests: **2 PASS**. They verify every existing REC-001 gate, the
  ACTIVE status constraint, both participant orientations, and absence of invitation-state
  filtering. Ruff on the changed service/test files: **PASS**.
- The broader async-focused and full backend suites are deferred to Task 4 because the installed
  Windows AnyIO runner stalls before the first async test; the deterministic Task 1 tests are
  synchronous and completed normally. No Production or external database was used.

## Task 2 — complete 2026-10-16

- Recommendation cards now render only display name, student type, study program and compatibility
  percentage, followed by adjacent View profile and Send invitation actions. Avatar, profile lists,
  availability and score breakdown are no longer rendered on the cards.
- The existing bounded privacy-safe recommendation projection now allowlists the canonical full
  name, bio, study year, nationality and home-university columns in addition to its existing data.
  The profile dialog therefore needs no extra request and introduces no N+1 query.
- The selected-profile portal renders the requested avatar, names, bio, interests, preferred
  activities, languages, weekly availability, compatibility breakdown, study program, study year,
  nationality and home university. It uses shared profile/breakdown/avatar components and supports
  a visible close action, Escape, backdrop close, focus trapping/restoration, background isolation,
  scroll locking, bounded mobile overflow and consistent missing/empty fallbacks.
- Focused verification: backend allowlist/Task 1 schema tests **7 PASS**; frontend recommendation,
  page and matching-client tests **24 PASS**; TypeScript, focused ESLint, Prettier and backend Ruff
  **PASS**. The broader suites remain Task 4 gates.

## Task 3 — complete 2026-10-16

- Sent Invitation rows now render only the existing authorized avatar, recipient display name and
  Accepted/Pending status as profile/invitation information. Score, study program, student type,
  timestamps, interests, preferred activities, languages, availability and compatibility details
  are no longer rendered in this list.
- Pending rows retain their existing cancellation mutation, confirmation/error/success flow.
  Accepted rows retain the exact explanatory message, `/user/buddy` Start chatting destination and
  existing hide mutation. The backend hide path still only sets `sender_hidden_at`; it cannot alter
  the ACTIVE Match, conversation or messages.
- Focused invitation-page, invitation-contract and matching-client verification: **3 files / 32
  PASS**. Tests verify the reduced row content, both statuses, retained actions and the absence of a
  current-Buddy refresh/removal side effect after hiding an accepted Sent entry.

## Task 4 — complete 2026-10-16

| Check | Result |
| --- | --- |
| Task 1 backend SQL/allowlist focus | 7 PASS |
| Task 2 matching page/client focus | 3 files / 24 PASS |
| Task 3 invitation page/contracts/client focus | 3 files / 32 PASS |
| Full backend suite | 1,416 PASS / 37 explicit live-environment SKIP in disposable Python 3.12 container |
| Full frontend suite | 85 files / 812 PASS with two workers; the earlier default-worker run's 5 unrelated timing failures also passed in a 4-file / 56-test serial rerun |
| Backend Ruff / strict mypy | PASS / PASS (292 source files) |
| Frontend TypeScript / ESLint / Prettier | PASS / PASS / PASS |
| Frontend production build | PASS; existing large-chunk advisory only |
| Live authenticated browser / Production | NOT RUN; no account, Production write, push or deployment was authorized |

The matching and invitation checklist is covered by the focused DOM/service tests and source-path
inspection, including selected-profile identity, missing-data fallbacks, dialog close/focus/scroll
behavior, responsive wrapping/overflow classes, send/cancel/hide actions, accepted relationship and
conversation preservation, server order and pagination. A live authenticated desktop/mobile visual
pass was not performed and is not inferred from the automated evidence.

## Acceptance

- Established Buddies are absent from each other's recommendations in both directions; pending and
  unrelated users keep the existing behavior.
- Recommendation cards contain only the four requested fields and View Profile / Send Invitation
  actions. The dialog always reflects the selected profile, supports all requested safe fields and
  compatibility breakdown, handles missing values, Escape, backdrop, focus and scroll isolation.
- Sent entries contain only avatar, user name and status as profile/invitation information. The
  accepted explanation, Start chatting link and both removal paths retain their current behavior;
  removing an accepted entry cannot delete the Match or conversation.
- Focused regression, lint, type-check and production-build evidence supports completion. Manual
  items that cannot be exercised locally are reported explicitly rather than inferred.
