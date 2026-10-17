# Testing and evidence

Tests prove the scenario and environment actually exercised. A unit test cannot establish
Production readiness; a successful page load cannot establish transactional race safety.

| Layer                          | Repository location                                  | Purpose                                                                                           |
| ------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Frontend pure functions        | `apps/web/src/features/**/*.test.ts`                 | Parsing, scoring presentation, navigation and safe URL/state helpers                              |
| Frontend component/integration | Adjacent `.test.tsx`, Testing Library, Vitest/jsdom  | Role/bootstrap, onboarding, invitations, chat, Event errors and accessibility behavior            |
| Backend unit/service/API       | [tests](../../../apps/api/tests/conftest.py), pytest | Business rules, negative auth, DTOs, service behavior and HTTP contracts                          |
| Live integration               | Explicitly opted-in `_live` suites                   | Real PostgreSQL constraints, locks, rollback and Storage behavior; never assume default execution |
| Migration/static/package       | Alembic graph, Ruff, mypy, package build             | Schema ordering, typing/style and reproducible packaging                                          |
| Browser acceptance             | Task/operations records                              | Real rendering, responsive overflow, decoded images, keyboard/locale flows and console/network    |
| Release/Production             | Exact-SHA CI/provider and bounded smoke records      | Deployed artifact, flag, first-party security and health evidence                                 |

## Current CI contract

[ci.yml](../../../.github/workflows/ci.yml) uses Node 24 for the frontend and Python 3.12
for the API. Frontend runs locked install, format, lint, typecheck, tests, build and runtime
dependency audit. Backend runs locked install/pip consistency, Ruff, mypy, pytest, Alembic
history/heads, package build, runtime dependency audit and Compose validation.

Normal local commands are in [frontend package scripts](../../../apps/web/package.json) and
[backend instructions](../../../apps/api/README.md). Opt-in live tests require an isolated
environment; absent configuration means SKIP, not PASS. Do not execute destructive or external
tests merely to update this knowledge base.

## High-value regression map

| Change                | Meaningful scenarios / focused evidence                                                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auth/session          | Invalid CSRF, wrong role, refresh reuse, logout/reload and private-cache clearing                                                                          |
| Profile               | Stale version, missing/incomplete profile, ready avatar ownership, ACTIVE type lock                                                                        |
| Recommendations       | Exact weights, empty sets, normalized custom values, timezone overlap, deterministic ties/capacity and both ACTIVE pair orientations                       |
| Invitations           | Duplicate sends, expiry at action time, recipient-only accept, concurrent accept and atomic conversation/outbox                                            |
| Chat                  | IDOR, retry identity, disconnect/REST recovery, read markers, unread hints and expiry cleanup                                                              |
| Events                | DRAFT/deleted exclusion, CANCELLED detail versus slider, null schedule, legacy MEMBERS eligibility, ready owned cover, stale 409 and optional registration |
| Frontend Event parity | Same cache/selector/order, dashboard return marker, direct-link refresh and independent strict flags                                                       |
| Semester              | Status refetch never prepares, reauth/phrase/write barrier, failed/unverified backups, new-user irreversible restore block and cohort isolation            |
| Landing               | Decode-safe transitions, reduced motion, EN/DE, keyboard walkthrough, hash offsets and viewport overflow                                                   |

Examples: [Matching tests](../../../apps/api/tests/test_matching_scoring.py),
[invitation concurrency](../../../apps/api/tests/test_invitation_acceptance_live.py),
[slider API](../../../apps/api/tests/test_event_sliders_api.py),
[frontend shared Event tests](../../../apps/web/src/pages/user/user-dashboard-events.test.tsx).

## Retained acceptance, not new test results

`EVS-007` records supported-runtime recovery of two test-harness WSS races. Later Event
acceptance records 1,408 API PASS / 37 SKIP and 774 frontend PASS at that historical boundary.
The Oct 16 Matching task records 1,416 API PASS / 37 SKIP and 812 frontend PASS; About at
baseline records 23 focused tests plus static/build/browser gates. These counts belong to
their commits and scope; they are not a fresh full-suite result for this audit.

See [validation ledger](../../implementation/validation.md) and the
[task index](../../implementation/task-index.md). Accepted gates were preserved. This change
validates documentation links, task coverage, Git scope, revision references and sensitive-value
patterns; application regression is unnecessary because application bytes are unchanged.
