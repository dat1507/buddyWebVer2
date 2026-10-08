# PROD-001 technical evidence closure — 2026-10-08

**Observation window:** 2026-10-08 14:15–15:01 Asia/Saigon

**Reviewed Git baseline:** `2c66a227edc4aa2d41a1676de2c93d93d52f1e6f`

**Decision:** **BLOCKED / OWNER ACTION REQUIRED**

**Source/provider configuration/destructive data change:** no. The existing chat's ordinary
idempotent read marker may have reconciled when the conversation was opened.

This record closes the technical checks that can be proved safely without repeating the owner's
accepted functional smoke or performing a privileged configuration/destructive mutation. It does
not mark `PROD-001` DONE. A failed
Production semester-backup preparation, the missing retained Render rollback point and unnamed
rollback/recovery owners remain mandatory blockers.

## Deployed baseline and public health

| Item | Dated evidence | Result |
| --- | --- | --- |
| Git control-plane baseline | `main` and `origin/main` both at `2c66a227` before this documentation update | PASS |
| Vercel frontend | project `buddy-web-ver2`; deployment `dpl_FZAGsVudHtTiWkomWHBbV7J5k6MB`; deployment URL `buddy-web-ver2-6mscyuphg-dat1507s-projects.vercel.app`; Git `2c66a22`; Ready | PASS |
| Vercel retained candidates | Ready deployments `8j6KqoBAuLZZAkCuEkCVUQgutV1E` (`c62b055`) and `xDkv4ZvDdr6oZfAqmixXfVJdGg64` (`81979ce`) remained selectable | PASS |
| Render backend | service `srv-db343ne7bikc73bjv910`; deployment `dep-db343nu7bikc73bjvalg`; Git `d15cb1d7c380e12e8f66e38f5573d191415d6913`; Live | PASS |
| Render retained candidate | dashboard reported only one deploy for the service | **BLOCKED** |
| Database compatibility | retained verified migration head `0021_restore_runtime_permissions`; no migration was run | PASS |
| Public probes | frontend, `/api/health/live`, and `/api/health/ready` returned 200; anonymous `/api/auth/me` returned 401 | PASS |
| Render observation | no dashboard events in the preceding 12 hours; no `ERROR` log match in the preceding hour; repeated platform live probes returned 200 | PASS for the observed window |

The Vercel and Render dashboard reads were non-mutating. No rollback, promotion, redeploy or
provider-setting change was performed.

## Acceptance reconciliation

| Gate | Previous status | New status | Evidence | Remaining action |
| --- | --- | --- | --- | --- |
| DNS, TLS, health, readiness, API target and exact-origin CORS | PASS | PASS | Reused direct 2026-10-08 public evidence; fresh frontend/live/ready probes remained 200 | None |
| Owner functional smoke | PASS | PASS | Dated owner acceptance for Admin/User dashboards and Recommendation -> Invitation -> Accept -> Match -> Chat | Do not repeat |
| Secure host-only cookies | VERIFY | PASS | Authenticated browser exposed only metadata: access, refresh and CSRF cookies used the `__Host-` prefix, API host-only scope, `/`, Secure, HttpOnly and SameSite=Lax; access and refresh/CSRF lifetimes matched the short/long design | None |
| Session persistence/recovery/logout | VERIFY | PASS | Reload retained the USER session; CSRF session and `/auth/me` returned 200; targeted refresh/expiry tests passed; UI logout returned 204 and removed all three cookie names | None |
| CSRF negative path and private caching | VERIFY | PASS | Targeted API/web tests cover missing, invalid, duplicate and retry/recovery paths; live first-party mutation succeeded through the UI; live cross-origin CORS rejection was retained. No risky negative mutation was sent to Production | None |
| Authenticated WSS, Origin and unauthorized handling | VERIFY | PASS | Authenticated notification and conversation WSS handshakes returned 101 with Origin `https://www.vgubuddyprogram.com`; allowed-origin/unauthenticated and foreign-origin/unauthenticated handshakes returned 403; source order and targeted tests cover authenticated Origin/auth enforcement | None |
| WSS reconnect and REST recovery | VERIFY | PASS | Page reload created fresh conversation and notification WSS handshakes (101) and refetched conversation history over REST (200); no chat message was sent | None |
| Semester authorization and destructive guards | VERIFY | PASS | Authenticated ADMIN GET `/api/admin/semesters/management` returned 200; UI exposed only guarded Prepare controls, reported `NEW_COHORT` restore blocking, and no Prepare/Execute/Reset/Restore action was invoked | None |
| Private semester-backup access | VERIFY | **FAIL** | Read-only status reported reset `FAILED` / `RESET_PREPARATION_FAILED`, backup `FAILED`, no verification or expiry; Render showed two earlier `POST /reset/prepare` responses of 503 | Repair and separately authorize a safe verification; do not retry from this task |
| Secret/history scan | VERIFY | PASS | High-confidence key/JWT/private-key/provider-token patterns found no matches in tracked content or full Git history; credential-URL matches were restricted to localhost fixtures/examples; no tracked secret/env/key files were found | Keep normal rotation and scanning policy |
| Credential rotation and destructive-control review | VERIFY | PASS | Reused the dated Upstash rotation and isolated Production credential evidence; source/tests confirmed Admin, CSRF, current-password, exact-phrase, lock and fail-closed controls | None |
| Hold telemetry | VERIFY | PARTIAL | Public health remained healthy; 12-hour Render event view was quiet; one-hour `ERROR` query had no match; WSS and retained maintenance-path evidence exist. No owner-approved hold duration was named | Owner must define/accept the hold duration after blockers are repaired |
| Frontend rollback readiness | VERIFY | PASS | Current and two prior Ready Vercel deployments were retained | Name the executor/decision owner |
| Backend rollback readiness | VERIFY | **BLOCKED** | Render service had only the current deployment; no prior retained deploy was selectable | Establish a compatible retained deploy or an approved immutable redeploy procedure |
| Database recovery reference | VERIFY | PARTIAL | Schema-compatible rollback boundary and DR runbook exist; full encrypted off-site snapshot/restore rehearsal remains intentionally open | Complete under post-deploy DR hardening |
| Named rollback/recovery owners | VERIFY | **BLOCKED** | No names were supplied; none were inferred | Assign decision, frontend, backend and database-recovery owners |

## Targeted automated verification

The checks were run against the reviewed checkout without Production credentials.

- Web: 5 focused files, 60 tests PASS covering session client, chat client/conversation/unread and
  Admin Semester UI.
- API: 143 focused tests PASS covering cookie issuance/clearing, CSRF, session API, realtime chat,
  health, Semester management/reset/restore and backup verification. One initial temporary-directory
  permission error was rerun with a repository-local pytest base directory and passed; it was not an
  application failure.
- The previously recorded full release baseline remains 721 web tests and 1,330 API tests. It was
  not rerun because no application source changed.

## Browser and data-safety note

No credential, password, cookie value, token, message body, email address, participant identifier,
private object key or signed URL was recorded. Opening the existing conversation caused the product
UI to invoke its normal idempotent `messages/read` endpoint; a subsequent call returned 204. This
may have reconciled the current USER's read marker, but it created, edited and deleted no message
and changed no Buddy relationship. USER and ADMIN sessions were both logged out afterward and the
three auth/CSRF cookie names were absent.

## Mandatory owner actions

1. Approve a separate remediation task to diagnose and repair the Production semester-backup
   connection/storage configuration. Verification must be explicitly authorized because Prepare
   creates operation/backup metadata and reads private Production data.
2. Establish one compatible retained Render rollback point, or approve and document an immutable
   redeploy procedure for `d15cb1d7` that remains compatible with migration head `0021`.
3. Supply names for: rollback decision owner, Vercel executor, Render executor and database-recovery
   owner. One person may hold multiple roles if the owner explicitly chooses that assignment.
4. State the accepted post-repair observation duration. The completed 12-hour quiet observation is
   retained and does not need to be recreated; only the additional agreed window must be observed.

## Phase 2 readiness

- `ACCEPT-001` still lacks inert maximum-length rendering, true stale-tab/race evidence, physical
  expired-message deletion, the consolidated signed/redacted record and the encrypted off-site DR
  rehearsal. Production cookie/session/WSS/recovery evidence from this record may be reused.
- The DR lane still needs one complete encrypted off-site snapshot, disposable full restore,
  checksum/count reconciliation, anonymous Storage rejection, measured RPO/RTO and a named owner.
- Phase 2 planning is READY. Phase 2 implementation is BLOCKED until `PROD-001` blockers are
  resolved, the hold is accepted and the next Task ID is explicitly selected.
- After `PROD-001`, the execution order remains residual `ACCEPT-001` evidence, encrypted off-site
  DR rehearsal, retention/maintenance proof, measured capacity review, then an explicit product
  decision before the deferred `EVT-005` chain.
