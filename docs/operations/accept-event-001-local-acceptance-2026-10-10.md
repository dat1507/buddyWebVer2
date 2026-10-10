# ACCEPT-EVENT-001 local acceptance evidence — 2026-10-10

## Boundary

This record closes the owner-approved isolated local A–E gate. It does not claim a cloud Staging
deployment, a Production deployment, Production write acceptance, canonical Production Event data
or permission to enable `VITE_EVENTS_LAUNCH_ENABLED`.

The candidate used a dedicated local PostgreSQL acceptance database, a separate local Redis key
prefix, local Supabase Storage and a loopback HTTPS proxy with a trusted local certificate. The
email worker was not running. Readiness reported database and Redis ready with email and Storage
configured. No Production database, Redis, Storage, email provider, account or Event row was used.

## Acceptance A–D

The API harness completed **79 assertions / PASS**. It covered Admin authentication, create/edit/
reload, optimistic-version conflict, cover upload/replacement/cleanup, lifecycle transitions,
public EN/DE list/detail, canonical slider order, short-lived signed HTTPS covers, persistence,
anonymous and USER denial, CSRF, IDOR, strict response allowlists and invalid-file rejection. Local
synthetic Events finished non-public (`DRAFT` or `CANCELLED`).

The real browser gate completed **PASS** for Admin login/list/edit, signed cover rendering, slider
failure and manual retry, canonical Landing rendering, click-through detail, English/German,
direct deep-link reload, desktop/mobile layout and the successful empty state after unpublish.
There were zero runtime exceptions and zero unexpected console errors. The browser cleanup returned
the exercised Event to a non-public state.

## Acceptance discoveries and fixes

- Event and Event-media models now eagerly fetch server-generated update defaults so an async
  response can project `updated_at` after commit without `MissingGreenlet`. A mapper regression test
  covers both write models, and the real edit/status/cover acceptance paths returned success.
- Public Event detail waits for session bootstrap and keys its private cache by viewer. This prevents
  bootstrap cache clearing from orphaning a direct-link query in an infinite loading skeleton.
- The live Landing section now renders the existing localized empty-state contract after a
  successful empty response.
- Admin Event list projection now derives phase with the same instant used by its phase filter. This
  removes a clock-boundary race found when the focused suite crossed an Event start instant.

## Quality Gate E

| Gate | Result |
| --- | --- |
| Focused final Event suite | 121 PASS |
| Backend full suite, CPython 3.12.10 | 1,408 PASS; 37 explicit opt-in live SKIP; 1 non-failing Starlette deprecation warning |
| Backend Ruff / strict mypy | PASS / PASS; 291 source files checked by mypy |
| Backend consistency / schema / package | `pip check` PASS; one Alembic head at `0021_restore_runtime_permissions`; sdist and wheel PASS |
| Backend runtime lock audit | PASS; no known vulnerabilities in the fully pinned runtime set |
| Docker Compose | PASS using the ignored local env file for interpolation only; no service mutation |
| Frontend full suite | 84 files / 774 tests PASS |
| TypeScript / ESLint / Prettier | PASS / PASS / PASS |
| Normal / launch-mode builds | PASS / PASS; existing large-chunk warning only |
| Launch-mode static Event titles | None of the five legacy fallback titles present in launch-mode JavaScript |
| Frontend production dependency audit | PASS; 0 vulnerabilities |
| Landing canonical cap | First five API results; backend 12-row query bound unchanged |

The first backend full-suite attempt encountered only Windows system-temp permission errors in 25
`tmp_path` setups. A rerun with a fresh workspace-local `--basetemp` completed with exit code zero.
The strict lock audit likewise used its documented no-resolution mode against every exact pin after
the Windows MSYS interpreter could not build a cryptography audit environment; the vulnerability
query itself completed successfully.

## Result and next gate

**Local acceptance A–E: PASS.** The next authorized step is read-only Production baseline and
rollback preflight. No push or deployment is safe until an executable Vercel and Render rollback
path is verified. The Production Event flag remains OFF, and Event launch approval remains a
separate owner decision.
