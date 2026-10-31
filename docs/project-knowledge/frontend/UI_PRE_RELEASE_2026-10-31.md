# Accepted UI pre-release verification — 2026-10-31

**NO-GO — RELEASE BLOCKED.** Local verification and candidate preparation complete; no release performed.
Approved UI: `c1e04e96cd8f3172ae2a38d5bf6333ec0ae34c5e` (`codex/ui-consistency-demo`).
Candidate: local `codex/ui-release-rc`, based directly on freshly fetched main
`e1a2cc59bf6feb7e4b4f535c4d9ddb1a13854ee0`. Final SHA and exact file list are recorded in the
primary handoff and ignored `.local/ui-release/release-manifest.json` after local commit.
Worktree: `C:/Users/phuoc/Downloads/buddyWebVer2/.local/worktrees/ui-release-rc`.

## Recovery and scope

Recovered the uncommitted UI-only candidate, completed test logs, build hashes, provider readbacks,
52 passing API assertions and42 viewport scans. No previous certificate install/remove operation
was found. Docker and the review listener had stopped; task services were restarted, and the expired
four-hour disposable Storage service token was renewed without recreating its image files or users.
Resumed only TLS/Event integration, loaded-content accessibility, affected tests/builds and closeout.
Full suites were reused; their unchanged files remain valid, with affected Event tests rerun below.

The accepted presentation was selected onto current main; the entire demo branch was not merged.
All six unpublished local chatbot commits, backend additions, shared API/CSRF changes, demo
runtime/fixtures/hooks/routes, chatbot translations and unrelated work are excluded. Backend,
auth transport/guards, routes, flags, locks, CI and hosting configuration match main. Only six
approved UI locale namespaces were merged; production mounting stays main plus the shared stylesheet.
Existing assets and accepted visual layouts remain. Necessary nonvisual accessibility fixes:

- USER home accessible name includes its visible brand/home text.
- Event link names include the visible localized action and Event title.
- Event Details uses valid description-list grouping, with the existing classes/layout retained.

Original UI worktrees, main `9ec31fb` and six unpublished commits, primary dirty work and `.agents/`
are preserved. Candidate has no remote upstream. No backend/lock/provider change or visual redesign.

## Certificate and real Storage

Existing CA: `.local/tls/vgu-buddy-local-ca.crt`, subject/issuer `CN=VGU Buddy Local CA`.
SHA1 thumbprint: `CA3CBDDC007A362F6AC3674730FE9A3FC199BF3D`.
SHA256: `8B59172E4515899ABB44E80FAB3F24BBF8236B2419F363368F4450DFE7A297DF`.
This is the existing project-local development bundle; its names/purpose match
`scripts/generate_local_tls.py`. Historical creation provenance is not independently established.
The existing leaf chain validates to this CA and covers localhost/127.0.0.1/::1, valid until Dec2028.

Recovered read outside the sandbox: **Current User trusted; Local Machine absent**. An earlier
sandbox-limited read reported absent trust and was superseded by actual Windows chain validation.
**Zero Windows trust changes**: no CA imported, removed or regenerated, and the pre-existing entry
was preserved. Final state is checked again on closeout. No browser warning or TLS validation bypass.
Only the leaf key was mounted read-only into a task TLS listener; the API received the public CA
through its disposable SSL_CERT_FILE. CA private key was not used or exposed.

Root cause: HTTP local Storage URLs violated the unchanged API/frontend HTTPS image contracts.
The real slider API initially500 and Event Details error UI were retained as failed evidence.
Task-only HTTPS Storage fixes this environment issue: EN/DE feed200, real signed image retrieval
and decoding PASS; actual browser card → Details → Back and registration-link attributes PASS.
Registration-disabled absence was observed, then enabled only on the disposable synthetic Event
through the real Admin API. Reserved `.invalid` href, `_blank` and `noreferrer` verified; external
registration destination never opened. No Production feature or business rule changed.

## Critical gates

| Gate | Status | Recovered/final evidence |
| --- | --- | --- |
| Approved UI/security scope | PASS | Filtered UI-only candidate from e1; Zod4.6.6/Pillow13.0.0 retained. |
| Production demo isolation | PASS | Runtime physically absent; normal/demo-flag-true builds have23 identical files;10 forbidden markers absent in generated text. Actual `/__demo`404 and private login guard verified. |
| Full frontend regression | PASS, reused | 833 tests/88 files after home-name fix;576.75s. No rerun of unaffected tests. |
| Final affected Event regression | PASS | 42 tests/5 files on final semantic fixes; includes slider, details, EN/DE actions and feature-flag behavior. Earlier layout/guard39/4 also PASS. |
| Types/lint/format/build | PASS | Full static checks and both production builds rerun after final semantic fixes; existing >500KB bundle advisory. |
| Backend regression/static/package | PASS | Unchanged API:1421 PASS/37 opt-in SKIP; focused image/security93 PASS. pip check, Ruff, mypy294 files, migration graph/heads, package and Compose validation PASS. |
| Real isolated integration | PASS within stated limits | 52 earlier passing API assertions plus17 recovered Event/Storage assertions; actual browser profile/interest save/reload, Dashboard, Event card/details/Back/EN-DE and images. |
| Accessibility/responsiveness | PASS automated scope |42 prior cases (Event error states explicitly excluded as loaded proof) plus18 final loaded Landing/Events/Details cases × EN/DE ×1440/768/390;0 WCAG2/2.1 A/AA violations, overflow or broken decoded images.0 captured console errors. |
| Selected existing live auth | FAIL, existing |11 PASS/2 ADMIN fixture FAIL: promoted USER retains semester_id, violating ck_users_role_semester. |
| Fresh database migration | FAIL, existing |36-character0022 revision exceeds default alembic_version VARCHAR32. Task-only VARCHAR128 prerequisite allowed further tests; fresh install did not pass. |
| Runtime security audits | PASS | npm production0; Python3.12 locked backend36 packages/0 findings. |
| Full development audits | FAIL, existing locks | npm20 affected packages (3HIGH/17MODERATE); pip17 advisories in4 development packages. No suppression/autofix. |
| Exact-candidate hosted CI | UNVERIFIED | No publication authorized. Existing main run40998838510 Frontend+Backend PASS is not candidate CI. |

Real writes used only task-owned PostgreSQL/Redis/Supabase Storage and synthetic users/Event.
Covered password/cookie auth, authorization/CSRF denial, profile/stale409, interests/activities/
languages/availability, avatar upload/signed retrieval, matching EN/DE, invitation send/receive/accept
and buddy rows, USER denial at Admin API, actual Admin cover upload/publication and localized Events.
Email delivery and an actual external registration submission were not tested. Axe incompletes,
including image-backed contrast/manual ARIA items, remain in evidence; no full screen-reader claim.
No live OS reduced-motion emulation was performed; existing tests/scoped CSS are retained.

Harness corrections are disclosed: canonical language order and mandatory cover rule retained;
one resumed Event harness used PATCH instead of documented PUT (invalid measurement, then corrected).
A focused test attempt executed0 tests because sandbox TEMP imports were missing; outside-sandbox
retry without cached transforms passed42. Existing tests were not weakened or silently skipped.

## Deployment compatibility and rollback

Dated read-only provider evidence: Vercel buddy-web-ver2/prj_WZjPHgpxuEoRd393PEy8u0vt04ZX,
Production main/e1a2cc59/dpl_AxXsMEk5rXb7mS18x6MKmzdbswTw READY; apps/web, Vite, Node24.x,
default commands/no overrides. Both Production Event flags alreadytrue; API base freshly verified
after owner account verification as `https://api.vgubuddyprogram.com/api`. No setting changed.
Preview tracks all unassigned branches; future branch publication creates a Preview. Preview API
must be verified as an isolated authorized target before cloud authenticated testing.
`staging.vgubuddyprogram.com` is a Production alias and was not used for test writes.

Render vgu-buddy-api-production remains Live642fc11/main, apps/api, Docker/pre-deploy overrides empty,
**Auto-DeployOff**, PR PreviewsOff. Its API tree equals main/candidate. This is a **frontend-only**
release; no coordinated backend release or migration is required. Keep Render Auto-Deploy OFF.

Vercel retains current e1 security deployment and prior READY f88, with30-day Production retention;
Instant Rollback was available on prior f88 (menu inspected only). Planned recovery after a future
UI release is current e1, subject to fresh eligibility verification at release time. Do not recover
to f88, which would lose the Zod fix. No rollback or provider mutation occurred.

## Remaining work requiring separate authorization

1. Scoped remediation/disposition of the existing migration and two ADMIN fixture failures,
   preserving database constraints and applied migration history. No exception assumed.
2. Remediate/dispose of development findings: frontend source-map-js1.2.1, undici7.29.1, Vite8.2.2
   and affected tooling; backend msgpack1.2.2, certifi2026.7.22, filelock3.32.7, setuptools84.0.0.
   Rerun affected gates while retaining runtime security fixes.
3. After local critical gates are green, authorize candidate-only branch publication and automatic
   Preview, confirm isolated Preview API targeting, and obtain green exact-SHA hosted CI.
4. Only then request separate Production approval. No push, merge, main reset or deployment now.

Sanitized raw evidence and screenshots: primary ignored `.local/ui-release/`. Private fixture
credentials and task containers/network are removed at closeout; pre-existing services/trust kept.
See `cleanup.json`, `certificate-after.json` and `release-manifest.json` for final state.
