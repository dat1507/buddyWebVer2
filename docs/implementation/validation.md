# Documentation migration validation

**Migration date:** 2026-10-08

## Required invariants

- `AGENTS.md`, `SESSION_HANDOFF.md` and root `implementation-plan.md` exist.
- Every recognized Task ID in the legacy plan has a matching
  `docs/implementation/tasks/<TASK_ID>.md` extract and an entry in `task-index.md`.
- The lightweight plan links only to existing documentation paths.
- The legacy plan remains byte-complete except for the already-present current release-boundary note
  and the archive pointer added by this migration; pre-existing user documentation edits remain.
- No file under `apps/`, `supabase/` or application runtime configuration changes.
- No secret-like value is introduced.
- Markdown links and Task ID paths resolve.
- Production status distinguishes direct public checks, retained operator evidence, dated owner
  functional acceptance and unverified technical release gates.
- `git diff --check` passes.

## Validation record

Validation performed against the refactored worktree:

| Check                                            | Result                          |
| ------------------------------------------------ | ------------------------------- |
| Legacy plan before refactor                      | 677,480 bytes; 9,181 lines      |
| Legacy archive after pointer                     | 677,868 bytes; 9,186 lines      |
| Current lightweight plan                         | 8,499 bytes; 142 lines          |
| Extracted Task IDs/files                         | 212 / 212                       |
| Task extract payload                             | 939,196 bytes, split by Task ID |
| Missing/extra Task files                         | 0 / 0                           |
| Missing task-index entries                       | 0                               |
| Broken local links in the new documentation set  | 0                               |
| Application/source/config changes                | 0                               |
| Secret-pattern hits in the new documentation set | 0                               |

Status distribution: 152 DONE/PRESERVED, 1 IN PROGRESS/TECHNICAL VERIFY, 1 OPEN hardening, 13 deferred
post-deployment, 15 planned backlog, 26 superseded and 4 requiring a new contract.

Final whitespace, staged-diff, repository-status and commit checks are run after this record is
written. The final commit identifier is reported in the handoff response because a Git commit cannot
contain its own resulting hash.

## Result

**PASS.** Task coverage, current-status reconciliation, path resolution, source-scope, secret scan
and `git diff --check` passed. Migration commit `c62b055` was pushed to `origin/main`; the later
owner-acceptance synchronization is recorded below and its resulting commit is reported in the
handoff response.

## Owner-acceptance synchronization validation — 2026-10-08

| Check                                              | Result                                                    |
| -------------------------------------------------- | --------------------------------------------------------- |
| Required control-plane files                       | 10 checked; 0 missing                                     |
| Focused `PROD-001` source paths                    | 10 checked; 0 missing                                     |
| Task files / task-index links                      | 212 / 212                                                 |
| Unindexed task files / missing task links          | 0 / 0                                                     |
| Broken local links in the routed documentation set | 0                                                         |
| Changed files                                      | 11 documentation files; 0 application/source/config files |
| Added secret-pattern hits                          | 0                                                         |
| Legacy archive changes after `c62b055`             | 0                                                         |
| Whitespace validation                              | `git diff --check` PASS                                   |

The owner-confirmed functional paths are marked PASS without upgrading cookie/CSRF/WSS,
Semester/release-safety, hold or rollback gates. `PROD-001` therefore remains IN PROGRESS /
TECHNICAL VERIFY and is the next release-blocking task.

## PROD-001 technical-closure validation — 2026-10-08

This later validation supersedes only the final status sentence above; it does not rewrite the
historical migration result.

| Check                                                         | Result                  |
| ------------------------------------------------------------- | ----------------------- |
| Required routed control/evidence files                        | 8 checked; 0 missing    |
| Task files / unique task-index links                          | 212 / 212               |
| Broken local Markdown links in implementation/operations docs | 0                       |
| New technical evidence record                                 | 9,407 bytes; 100 lines  |
| Documentation files changed/added                             | 10                      |
| Application/source/runtime-config changes                     | 0                       |
| Legacy archive changes                                        | 0                       |
| Added high-confidence secret-pattern hits                     | 0                       |
| Focused web/API tests                                         | 60 / 143 PASS           |
| Whitespace validation                                         | `git diff --check` PASS |

Result: documentation reconciliation **PASS**. `PROD-001` itself is **BLOCKED / OWNER ACTION
REQUIRED**, not DONE, because direct evidence found the private Semester backup failed and unverified,
Render has no previous retained backend deploy, and named owners/post-repair hold approval are absent.
The resulting docs-only commit identifier and push status are reported in the session response.

## Phase 2 Landing/Home University implementation validation — 2026-10-08

| Check                                                    | Result                                                                                         |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Focused web tests                                        | 5 files; 33 tests PASS                                                                         |
| Landing tests                                            | slideshow 2/2; assembled Landing 8/8 PASS                                                      |
| Profile tests                                            | 3 files; 23/23 PASS                                                                            |
| TypeScript                                               | `npm run typecheck` PASS                                                                       |
| ESLint                                                   | `npm run lint` PASS                                                                            |
| Formatting                                               | `npm run format:check` PASS                                                                    |
| Production build                                         | `npm run build` PASS; existing large-chunk warning only                                        |
| Supplied/retained Landing images                         | 5 / 5; all decode successfully; 890,342 optimized bytes                                        |
| Backend/database/migration/matching/Event-slider changes | 0                                                                                              |
| Production/provider mutation                             | 0                                                                                              |
| Task files / unique task-index links                     | 214 / 214; 0 missing in either direction                                                       |
| Broken local links in routed/current docs                | 0                                                                                              |
| Added high-confidence secret-pattern hits                | 0                                                                                              |
| Whitespace validation                                    | `git diff --check` PASS                                                                        |
| Direct browser visual QA                                 | NOT RUN / MANUAL GATE — available browser surfaces timed out on the terminal-local Vite server |

Result: local implementation and automated verification **PASS**. Visual acceptance remains **OPEN**
and is not inferred from tests or build output. `PROD-001`, Backup/DR, `SEM-008` and residual
`ACCEPT-001` remain open. No push or deployment is authorized by this record.

## Phase 2 frontend Production release validation — 2026-10-09

| Check                                     | Result                                                                    |
| ----------------------------------------- | ------------------------------------------------------------------------- |
| Released commit                           | `2f6f8c8cb4bd15fb4ece1821e8cfc1b4ac3ea8f7` on `origin/main`               |
| Vercel Production deployment              | GitHub deployment `6951736865`; SUCCESS                                   |
| Repository checks                         | Frontend PASS; Backend PASS                                               |
| Production alias/bundle                   | 200; `index-Deo6vyVU.js`                                                  |
| Required bundle markers                   | 5 Landing assets + EN/DE Home University + first-party API target present |
| Landing desktop/mobile visual             | PASS at 1536x831 and 390x844; no horizontal overflow                      |
| Landing live transition                   | PASS; mid-fade opacity observed after the seven-second display interval   |
| Browser console                           | 0 errors; 0 warnings                                                      |
| Public API regression check               | live 200; ready 200; anonymous auth 401/no-store/exact-origin CORS        |
| Account/provider/database mutation        | 0; release push/deploy only                                               |
| Home University authenticated visual      | OPEN; no account used                                                     |
| Task files / unique task-index links      | 214 / 214; 0 missing in either direction                                  |
| Broken local links in routed/current docs | 0                                                                         |
| Added high-confidence secret-pattern hits | 0                                                                         |
| Documentation-only evidence delta         | 8 files; 0 application/runtime files                                      |
| Whitespace validation                     | `git diff --check` PASS                                                   |

Result: `FE-LANDING-BG-001` is **DONE / PRODUCTION VERIFIED**.
`FE-PROFILE-HOME-UNI-001` is **DEPLOYED / AUTOMATED PASS** with authenticated visual acceptance
still open. Phase 1 release blockers remain unchanged.

## Landing slideshow corrective release validation — 2026-10-09

| Check                                    | Result                                                                              |
| ---------------------------------------- | ----------------------------------------------------------------------------------- |
| Released source commit                   | `c2fbaf1f1082c6bb5d790d32add3b603f3b251fe` on `origin/main`                         |
| Vercel Production deployment             | `6952736000`; SUCCESS                                                               |
| Repository checks                        | Frontend SUCCESS; Backend SUCCESS                                                   |
| Complete frontend tests                  | 77 files; 730 tests PASS                                                            |
| TypeScript / ESLint / Prettier / build   | PASS / PASS / PASS / PASS                                                           |
| Local browser audit                      | 16 transitions desktop/mobile; all zero-error invariants PASS                       |
| Production browser audit                 | 15 desktop transitions plus mobile; 0 blank/undecoded/visible-source-change samples |
| Production layout / console              | 0 px layout delta; 0 px mobile overflow; 0 errors; 0 warnings                       |
| Production reload / reduced motion       | PASS / one static decoded first image PASS                                          |
| Task files / unique task-index links     | 215 / 215; 0 missing in either direction                                            |
| Landing asset changes                    | 0; five files/order and 890,342 bytes preserved                                     |
| Backend/database/provider-config changes | 0                                                                                   |
| Whitespace validation                    | `git diff --check` PASS before release-evidence commit                              |

Result: `FE-LANDING-BG-002` is **DONE / PRODUCTION VERIFIED**. The Profile authenticated visual
gate and existing Phase 1 operational blockers remain unchanged.

## Dynamic Event local implementation validation — 2026-10-09

| Check                                   | Result                                                                              |
| --------------------------------------- | ----------------------------------------------------------------------------------- |
| Canonical chain implemented             | `EVT-005/006/009/011`, `EVS-005`, `ADMIN-006..009`, `FE-031`, `FE-014B`             |
| Focused backend Event tests             | 96 / 96 PASS                                                                        |
| Backend Ruff / strict mypy              | PASS / PASS                                                                         |
| Backend full suite                      | 1,405 PASS; 37 SKIP; 2 unrelated WebSocket teardown FAIL on Python 3.14             |
| Frontend full suite                     | 84 files; 772 tests PASS                                                            |
| TypeScript / ESLint / Prettier          | PASS / PASS / PASS                                                                  |
| Normal / Event-launch production builds | PASS / PASS; existing large-chunk warning only                                      |
| Launch-mode static Event records        | 0 matching five legacy titles in built JavaScript                                   |
| Alembic graph                           | one head: `0021_restore_runtime_permissions`; no migration added                    |
| Event authorization/security            | ADMIN RBAC, USER/anonymous denial, CSRF, IDOR, DTO/key and URL-hardening tests PASS |
| Production/provider/database mutation   | 0; launch flag remains off                                                          |

Result: Event implementation and focused automation PASS. `EVS-007` remains **IN PROGRESS** rather
than DONE because the repository-wide backend gate is not fully green on the available Python 3.14
host. `ACCEPT-EVENT-001` remains NOT READY until that exception is confirmed and matching SHAs are
deployed to Staging; no Production flag or deployment is authorized by this record.

## Dynamic Event regression closure and Staging readiness — 2026-10-09

This later record supersedes only the open regression conclusion immediately above; it preserves
that earlier observation as history.

| Check                                     | Result                                                                                              |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Official runtime                          | CI and Docker target Python 3.12; verification used CPython 3.12.10                                 |
| Two prior WebSocket failures              | Test-harness cross-loop publish and asynchronous cleanup race; application WebSocket code unchanged |
| Exact former failing cases                | 2 / 2 PASS after portal publish and deterministic fake-subscription cleanup                         |
| Full backend                              | 1,407 PASS; 37 SKIP; one non-failing Starlette deprecation warning                                  |
| Focused backend Event tests               | 111 / 111 PASS                                                                                      |
| Ruff / strict mypy / `pip check`          | PASS / PASS / PASS                                                                                  |
| Backend package / Compose / Alembic       | sdist+wheel PASS / config PASS / one head at `0021_restore_runtime_permissions`                     |
| Backend production dependency audit       | No known vulnerabilities found                                                                      |
| Full frontend                             | 84 files; 773 tests PASS                                                                            |
| TypeScript / ESLint / Prettier            | PASS / PASS / PASS                                                                                  |
| Normal / Event-launch builds              | PASS / PASS; existing large-chunk warning only                                                      |
| Frontend production dependency audit      | 0 vulnerabilities                                                                                   |
| Landing Event maximum                     | First 5 canonical results; API bounded cap remains 12; no storage/Admin cap                         |
| Staging frontend                          | 200, but older static bundle without Admin Event implementation                                     |
| Staging API                               | live/readiness/Event-slider probes 503; provider reports suspended                                  |
| Isolated Staging dependencies/access      | Redis absent after Production reallocation; no local provider linkage/credentials                   |
| Staging scenarios A–E                     | NOT RUN — environment prerequisite blocked                                                          |
| Production mutation/deploy/push           | 0; launch flag remains off                                                                          |
| Task files / unique task-index links      | 215 / 215; 0 missing in either direction                                                            |
| Broken local links in routed/current docs | 0                                                                                                   |
| Added high-confidence secret-pattern hits | 0                                                                                                   |
| Legacy archive changes                    | 0                                                                                                   |
| Whitespace validation                     | `git diff --check` PASS                                                                             |

Result: `EVS-007` is **DONE**. `ACCEPT-EVENT-001` is **BLOCKED — ISOLATED STAGING STACK AND
PROVIDER ACCESS REQUIRED**, not FAIL. A matching Staging deployment and complete scenarios A–E are
still required before Production approval; pushing `main` is not a safe substitute because the
documented workflow may deploy Production.

## ACCEPT-EVENT-001 isolated local acceptance — 2026-10-10

This newer record supersedes only the obsolete cloud-Staging prerequisite and the historical
`NOT RUN` acceptance conclusion above.

| Check                                 | Result                                                                                                                 |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Local dependency boundary             | Dedicated PostgreSQL DB, Redis namespace, Supabase Storage and trusted loopback HTTPS; no Production dependency        |
| API acceptance A–D                    | 79 assertions PASS; synthetic Events left non-public                                                                   |
| Real browser acceptance               | Admin edit, retry, signed cover, detail/deep-link EN/DE, desktop/mobile and empty state PASS; 0 runtime/console errors |
| Acceptance regression fixes           | Async update-default projection, detail/session bootstrap, live empty state and phase-boundary projection covered      |
| Focused final Event suite             | 121 PASS                                                                                                               |
| Full backend, CPython 3.12.10         | 1,408 PASS; 37 explicit opt-in live SKIP; exit 0                                                                       |
| Backend static/package/security gates | Ruff, strict mypy, `pip check`, sdist/wheel, Compose config and exact-pin vulnerability audit PASS                     |
| Schema compatibility                  | One Alembic head at `0021_restore_runtime_permissions`; no migration added                                             |
| Full frontend                         | 84 files / 774 tests PASS                                                                                              |
| Frontend static/build/security gates  | TypeScript, ESLint, Prettier, normal/launch builds and production dependency audit PASS                                |
| Launch boundary                       | Production unchanged; Event flag OFF; no Event write/seed/publish/flag/provider mutation                               |

Result: isolated local acceptance A–E and Quality Gate E **PASS**. Continue with direct Production
baseline/compatibility and executable Vercel/Render rollback preflight. Deployment is blocked unless
both rollback paths are operationally proven. Detailed evidence is in
`../operations/accept-event-001-local-acceptance-2026-10-10.md`.

## ACCEPT-EVENT-001 controlled Production release — 2026-10-10

| Check                     | Result                                                                                                           |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Preflight baseline        | Vercel `253849d`; Render `d15cb1d`; public static bundle/health/auth boundaries verified                         |
| Production schema/Storage | Supabase ACTIVE_HEALTHY; Alembic `0021`; Event tables present; private 5 MiB JPEG/PNG/WebP bucket                |
| Compatibility             | No migration; additive backend APIs; flag-OFF frontend is skew-safe and retains five static posters              |
| Pre-push rollback         | Vercel READY candidate at `c2fbaf1`; Render specific-commit `d15cb1d` selection enabled deploy without execution |
| Released source           | `e2ef4c0cca7137ff319faa95d8e82672b0cc3bfc` on `origin/main`                                                      |
| GitHub Actions            | Run `38037425291`; Backend SUCCESS; Frontend SUCCESS                                                             |
| Vercel / Render           | `dpl_Evhx9hudQSBf99P9fxznxtGNg2GS` READY / `dep-db4v9lqvcj2c73e5jvlg` LIVE                                       |
| Post-deploy rollback      | Vercel candidate retained; Render native rollback to prior `d15cb1d` retained                                    |
| Public API smoke          | live/ready 200; auth 401/no-store; Event slider/list 200 empty; detail 404; Admin list 401                       |
| Frontend flag boundary    | `index-phrHnhsS.js`; five static titles present; canonical/Admin API markers absent                              |
| Browser smoke             | Landing desktop/mobile, Profile read and Buddy Matching read PASS; 0 warnings/errors                             |
| Production UI NOT RUN     | Admin Event and Event Detail intentionally hidden because flag OFF and Event total zero                          |
| Production mutation       | 0 Event/account/Storage/database writes; no seed/publish/flag/secret/provider change                             |
| Legacy archive            | Unchanged                                                                                                        |

Result: **DEPLOYED — FLAG-OFF PRODUCTION SMOKE PASS / AWAITING EVENT LAUNCH APPROVAL**.
`ACCEPT-EVENT-001` is DONE at the approved code-release boundary. Detailed evidence is in
`../operations/accept-event-001-production-release-2026-10-10.md`.

## ACCEPT-EVENT-001 final deployment verification — 2026-10-10

| Gate                  | Result                                                                                                                                                                      |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Git sync              | `HEAD == origin/main == e0ef343` before this local documentation addendum                                                                                                   |
| Docs-only CI          | GitHub run `38038014039`: Backend SUCCESS; Frontend SUCCESS                                                                                                                 |
| Vercel                | `dpl_3ndKHjjd57dNtye1X1k3Sw2Pd5HY` READY at `e0ef343`; bundle remains `index-phrHnhsS.js` with five static titles and no dynamic Event API markers                          |
| Render                | No docs-only deployment; `dep-db4v9lqvcj2c73e5jvlg` remains LIVE at `e2ef4c0`; prior `d15cb1d` retained with Rollback                                                       |
| Production health     | Site/live/readiness 200; database/Redis `ok`; email/Storage `configured`                                                                                                    |
| Production Event data | Direct read-only count: zero total/DRAFT/PUBLISHED/CANCELLED/cover-linked rows; slider 200 `[]`                                                                             |
| Launch flag           | `VITE_EVENTS_LAUNCH_ENABLED` absent in Vercel Production; compiled default OFF                                                                                              |
| Architecture          | One flag couples Admin and public surfaces; Admin create/edit routes are inconsistently outside the flag; safe Admin-ON/Public-OFF requires a separate approved code change |
| Production mutation   | None; no Event/account/Storage/database write, publish, flag, secret or provider change                                                                                     |

Result: the controlled flag-OFF deployment is fully verified. Production write acceptance and both
Admin/public activation approvals remain open. No full regression was repeated because application
source and dependencies did not change.

## EVENT-FLAG-SPLIT local release gates — 2026-10-11

| Gate                               | Result                                                                           |
| ---------------------------------- | -------------------------------------------------------------------------------- |
| Resolver strictness                | 11 / 11 PASS: exact true only; missing/invalid OFF; legacy true ignored          |
| OFF/OFF                            | 8 / 8 integration tests PASS; Admin/public routes hidden; Landing static         |
| ON/OFF                             | 8 / 8 PASS; Admin management visible; Landing static                             |
| OFF/ON                             | 8 / 8 PASS; Admin management hidden; public live surfaces visible                |
| ON/ON                              | 8 / 8 PASS; both independent surfaces visible                                    |
| Missing new flags + legacy true    | 8 / 8 PASS; both surfaces OFF                                                    |
| Invalid new flags + legacy true    | 8 / 8 PASS; both surfaces OFF                                                    |
| Focused affected regression        | 7 files / 67 tests PASS, plus 11 resolver tests                                  |
| Full frontend on final source      | 85 files / 788 tests PASS                                                        |
| TypeScript / ESLint / Prettier     | PASS / PASS / PASS                                                               |
| Four production-build combinations | PASS; existing large-chunk advisory only                                         |
| Final OFF/OFF rebuild              | `index-DVJeT1wu.js`, 888.63 kB / 246.32 kB gzip; PASS                            |
| OFF/OFF artifact boundary          | Five static titles present; slider endpoint and Admin Event route markers absent |
| Backend / local Event acceptance   | Not repeated; no backend change and no regression reason                         |
| Production mutation                | None; both new keys absent/OFF; no Event/database/Storage/Redis/provider write   |

Result: frontend implementation and local release candidate are **PASS**. Continue only with the
already authorized controlled frontend rollout and read-only OFF/OFF smoke. Admin-only activation,
public-live activation and Production Event write acceptance remain separate approval gates.
