# Zod remediation and Pillow synchronization — 2026-10-30

Local integration branch: `codex/security-main-sync`, based on freshly verified remote main
`f88c18dbc8cf5f62ff1e4184b9ad38375b1faab2`. Pillow commit A:
`00933ca181d9d725ca906983f9e6fbc7c5aa2e4b`; Zod commit B contains this record.

## Scope and integrity

A cherry-picks only the four approved files from deployed `642fc11` (pyproject, runtime/dev locks,
focused image security tests). The entire backend Git tree equals deployed 642fc11. Pillow is
13.0.0 in both locks. No migrations or business rules change. B updates only the web manifest/lock
and this necessary report: Zod 4.5.4 -> 4.6.6; no other resolved package version changes.
No TSX, schemas, payloads, translations, UI, provider settings or database records change.

Zod is a direct production dependency used in authentication, profiles, matching, invitations,
Events/admin and chat validation. [Official advisory](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5)
identifies a HIGH memory-exhaustion issue in failing oversized collections, patched in 4.6.6.
Existing profile collection/duplicate/proficiency bounds and chat limits remain intact; some API
collection schemas remain unbounded. No unbounded resource-exhaustion test was performed.

## Verification

- PASS frontend: 831 tests / 87 files, TypeScript, ESLint, formatting and production build.
  Includes auth, profile/catalog limits, Dashboard, Events, matching, chat and EN/DE coverage.
  Unmocked application fetch was blocked; no live accounts or Production services used.
- PASS production npm audit: zero findings; Zod advisory absent.
- FAIL full npm audit: six dev-only findings, three HIGH (source-map-js, undici, vite), three
  MODERATE (@vitest/mocker, postcss-selector-parser, vitest), zero critical. These affect development/
  build/test tooling and merit a separate targeted remediation; a clean production audit does not
  mean the toolchain is fully secure. No audit checks suppressed or dependencies broadly upgraded.
- PASS native Python 3.12.10/Pillow 13: 1,421 tests; 37 explicit opt-in service tests SKIP.
  Ruff, mypy (294 files), pip check, source Alembic history/heads and wheel/sdist builds PASS.
- PASS strict runtime-lock audit: 36 audited dependencies, zero affected, zero skipped.
  Embedded Python lacked venv; full Python 3.14 was used solely as audit tooling on the exact lock.
  Application runtime validation remains Python 3.12.
- PASS fresh production Docker build and isolated runtime: Python 3.12.14, Pillow 13.0.0,
  UID 10001, all 37 runtime pins match; JPEG/PNG/WebP orientation and metadata checks PASS;
  bounded EXIF path 0.019s. No external network/services. Internal HTTP live 200, anonymous profile
  401, readiness 503 expected with no database/Redis configured; this is not integration readiness.
- PASS Linux/container checks: focused image tests 93 PASS, full backend 1,421 PASS / 37 SKIP;
  Ruff, mypy, pip check, Alembic graph and package build all PASS, with network disabled.

Existing large frontend chunk and deprecated ESLint warnings remain. The earlier two ADMIN live
fixture failures reproduce with both Pillow versions; corrected temporary fixtures passed previously.
Fresh-database migration revision length (36 characters / VARCHAR(32)) remains a separate defect.
No migrations are added or executed by this fix. Current opt-in skips are not a fresh stateful
integration PASS; prior real HTTP/Storage evidence is reused only because backend source is identical.
Evidence/harness lives in ignored `.local/security-main-sync/` in the primary workspace.

## Git and operational boundary

Local main `9ec31fb` contains six unpublished chatbot commits and is deliberately unchanged;
remote main remains f88. Landing 316832c, UI 50d3d7a, security 8c02dfb and deployed/hotfix 642fc11
remain preserved. No historical branch merge. Primary dirty documentation and owner `.agents/`
remain separate. Hosted CI is PENDING publication approval; local checks do not claim hosted CI PASS.

Owner manually verified Oct30 Render vgu-buddy-api-production / srv-db343ne7bikc73bjv910:
Live 642fc11, tracked main, Auto-Deploy Off. Browser policy blocked direct reinspection; this is
owner-supplied current evidence, not an independent dashboard observation. Keep Auto-Deploy OFF.
Vercel connector Oct30 confirms Production Ready at f88 (dpl_FWA7zU9v9KKqLf4ysb9DYGMYcuCZ).
Last observed Preview rule covers unassigned branches; current connector does not expose Git rules,
so publishing this branch requires approval for its possible Preview. Workflow push/PR runs frontend
and backend CI; no workflow deployment job. No branch push, main update, merge or deployment yet.

Next: approve exact integration-branch publication plus possible Vercel Preview, run hosted CI, then
separately approve any main synchronization/Production release. No deployment authorization is inferred.
Keep remaining toolchain advisories, migration/fixture maintenance and UI redesign separate.
Landing redesign remains paused pending security synchronization disposition.
