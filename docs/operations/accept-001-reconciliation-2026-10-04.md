# ACCEPT-001 evidence reconciliation — 2026-10-04

## Decision

`ACCEPT-001` is **not closed**. The operator confirmations accumulated during staging are valuable
evidence, but they do not yet cover every explicit scenario in the acceptance contract and are not
assembled into the required signed, redacted record. This decision avoids rerunning confirmed
happy-path work while keeping production fail-closed.

The deployed staging baseline reported by the operator is commit `3e0b819`, with database revision
`0021_restore_runtime_permissions`. The operator also confirmed that the accounts were restored;
the Admin UI showed the expected immutable “This backup has already been restored” state with
aggregate backup counts. This supports successful restore and idempotency evidence. It does not
prove the distinct required scenario in which a second restore is rejected because a newly created
USER/new cohort now exists.

## Reusable operator-confirmed evidence

Do not repeat these flows merely to collect another screenshot. Instead, attach their existing UTC
deployment/API/provider records to the final acceptance record and have the responsible owner sign
them:

- new USER registration, real email verification and completed profile;
- invitation send and recipient Accept;
- subsequent authenticated login;
- email change followed by verification;
- migration to revision `0021_restore_runtime_permissions`;
- Semester reset/restore resulting in the expected three-account/three-profile aggregate dataset;
- restored accounts visible/usable after restore;
- Admin staging login and Semester status inspection;
- staging deploy of commit `3e0b819`.

Chat messages, account identifiers, addresses, cookies, verification links, object keys, signed
URLs and provider response bodies must not be copied into the record.

## Evidence still required to close

1. Record the exact staging invitation boundaries: 500/501 non-whitespace runs and
   10,000/10,001 Unicode code points, including trimmed submission and inert plain-text rendering.
2. Record backend rejection plus stale-tab UI handling for `student_type` change after Accept, and
   the Accept-versus-update race/load test with the existing Match unchanged.
3. Tie the operator's second-account/Accept work to the explicit multiple-Buddies assertion, then
   record Current Buddies, accepted email, two-party chat/read state, F5/logout/login recovery and
   physical retention cleanup.
4. Attach redacted Admin reconciliation evidence for the same test users and relationships.
5. Run the separate post-restore blocking rehearsal: after a completed reset/restore, create the
   attributable new USER/new cohort, prove restore is rejected before any write, and prove the old
   deleted account's type lock does not attach to a genuinely new registration.
6. Capture the complete candidate revision's automated suites plus live Redis, Storage, email,
   WSS, accessibility and shared validation/race gates. Existing unit coverage is supporting
   evidence, not a replacement for deployed behavior.
7. Complete one encrypted off-site backup and one disposable restore rehearsal under the DR plan.

## Newly reconciled evidence — maintenance scheduler

The free scheduled maintenance path is now accepted on staging for commit `5b20c00`. The operator
confirmed successful Cron health after at least two schedule intervals and all three sanitized API
completion events; independent probes confirmed live/ready 200 and generic unauthenticated 401.
See [the maintenance staging evidence record](maintenance-staging-evidence-2026-10-04.md). This
closes the maintenance item formerly listed among the missing `ACCEPT-001` evidence. Isolated
production Cron/Vault configuration remains a `PROD-001` provisioning step, not a reason to rerun
staging acceptance.

## Interim staging observations — remaining non-destructive scenarios

The following observations were made against the deployed staging UI on 2026-10-04. They are
redacted: no account address, cookie, profile/conversation identifier, invitation body, chat body,
signed URL or provider payload is recorded here.

- Invitation composer boundary UI: exactly 500 non-whitespace runs was enabled and 501 was rejected
  with the word-limit message. Exactly 10,000 supplementary-plane Unicode code points was enabled
  and 10,001 was rejected with the code-point-limit message.
- Canonicalization/backend path: a leading/trailing-whitespace payload whose raw length was 10,002
  code points and whose trimmed value was exactly 500 words/10,000 code points remained enabled.
  Submission reached the authoritative active-relationship rejection. Source order confirms message
  canonicalization/validation runs before that relationship check, so the exact trimmed boundary
  passed backend validation without creating a duplicate invitation. This does not yet prove
  deployed inert rendering because no new invitation row was created.
- Post-Accept profile UI: the current International-student radio was selected, both participation
  type radios were disabled, and the UI explained that an active Buddy match locks the type while
  other profile fields remain editable. A true pre-Accept stale tab and the transactional
  Accept-versus-update race were not recreated against shared staging.
- Multiple-Buddy/Admin reconciliation: the read-only Admin view showed 3 participants, all 3
  verified, 2 active matches, 0 participants with zero Buddies, 2 accepted invitations and no
  other invitation states. The shared Vietnamese participant showed 2 active Buddies; each of the
  two International participants showed 1. Admin detail and the USER Current Buddies view agreed
  for the acceptance USER. A separate authenticated session for the shared Vietnamese participant
  also showed both International Buddies in Current Buddies.
- Chat recovery: the existing private conversation displayed messages from both participants. All
  three visible messages survived F5/HTTP history recovery, the authenticated realtime status
  returned to connected, and the browser console contained no errors. After logout and a fresh
  manual login, Current Buddies still showed the same active relationship; reopening the
  conversation restored all three messages, realtime returned to connected and the console again
  contained no errors. This closes the F5/logout/login recovery observation, but not a separately
  attributable unread-to-read transition or physical retention deletion. In a later two-session
  check, one acceptance-only message was sent after explicit operator confirmation while the
  recipient remained on Dashboard. The recipient's global navigation, Dashboard Buddy card and
  matching Current Buddies card each reconciled to exactly 1 unread message. Opening that exact
  conversation displayed the new message and cleared the unread indicator; F5 retained the full
  history, kept unread at zero and restored the realtime-connected state. This closes the
  attributable unread-to-read transition.
- Supporting automated checks on the current checkout passed: 52 backend profile/profile-API/
  invitation-send tests and 25 frontend invitation/profile/chat component tests. The dedicated
  PostgreSQL race test remains guarded for an isolated loopback database and explicitly forbids
  staging; it was not run because the local Docker daemon was unavailable.

These observations do not close the remaining gaps: deployed inert invitation rendering,
backend stale-tab conflict display, the isolated Accept-versus-type-update race, attributable
physical expired-message deletion, the signed evidence record, DR rehearsal, and the final
`restore-blocked-after-new-USER` scenario.

### Final Semester rehearsal preflight — stopped before destructive execution

The read-only Semester status initially showed a current-semester post-reset account marker of
zero, the earlier Reset and Restore as completed, and the retained backup as Ready but already
restored. A new **Prepare reset and backup** operation was started to obtain the distinct unused
backup required by the final new-cohort blocking rehearsal. This preparation created backup/
operation metadata and began verification; it did not execute Reset and did not retry Restore.

The authoritative reset preflight reported zero student accounts, profiles, preferences,
invitations, Matches, conversations, messages and avatar objects for the current semester, while
preserving one Admin, 13 Interests, 8 Languages, 13 Activities and the existing backup records.
The apparent mismatch with the separate Matching view's three usable participants and two active
Matches was resolved with a read-only, aggregate-only database audit: the `CURRENT` semester has
marker 0 and 0 persisted USER rows, while the single `CLOSED` source semester has marker 3 and 3
persisted USER rows. Exact Restore retained the source semester ownership, so the current-semester
reset scope is correctly empty rather than silently omitting current-cohort data.

A second read-only audit confirmed that the database and avatar manifests and both checksums are
attached, the aggregate backup contains 0 rows and 0 avatar objects, `verified_at` is present and
`expires_at` is not. The observed backup `CREATING` / operation `RUNNING` pair is therefore the
expected pre-execution two-phase state: the reset preflight is executable, and the backup becomes
`READY` with its 30-day expiry only after Reset succeeds. No Reset or Restore was executed during
this audit. Destructive execution remains paused for an explicit action-time confirmation.

### Reset execution and second-Prepare anomaly

After explicit action-time confirmation, the operator entered the Admin credential and exact
confirmation phrase and executed the prepared empty-current reset. A later aggregate-only,
read-only audit established the following durable result:

- the reset requested at `2026-10-04 16:51:35 UTC` succeeded at
  `2026-10-04 17:08:26 UTC` (`00:08:26` on 2026-10-05 in Asia/Saigon);
- its source semester is `CLOSED`, its backup is verified and `READY`, and the newly created
  `CURRENT` semester started at the same completion instant with marker 0 and 0 persisted USERs;
- the three restored USERs remain on the earlier `CLOSED` source semester with 3 profiles,
  2 custom preferences and 2 accepted invitations;
- the same source semester still owns 2 ACTIVE Matches, 2 conversations and 4 messages;
- there is still exactly one prior successful Restore operation, completed before this reset; no
  Restore operation was created or retried after it.

The audit also preserved, rather than hiding, an anomaly: a second reset preparation was requested
at `2026-10-04 17:09:10 UTC`, 43.6 seconds after the successful reset. It targets the new empty
`CURRENT` semester and remains `RUNNING`; its verified backup remains `CREATING`. No second reset
execution, Restore retry, SQL cancellation or direct operation/backup mutation has been performed.

Render application logs resolve the immediate request origin without over-attributing the human
interaction:

- the first preparation had an `OPTIONS` preflight at `16:51:34 UTC`; its separate browser-originated
  `POST /api/admin/semesters/reset/prepare` completed at `16:51:41 UTC` after 6.494 seconds;
- the valid execution had an `OPTIONS` preflight at `17:08:22 UTC`; its
  `POST /api/admin/semesters/reset/{operation_id}/execute` completed at `17:08:28 UTC` after
  6.028 seconds, followed by read-only preflight/status refreshes;
- a new `OPTIONS /api/admin/semesters/reset/prepare` appeared at `17:09:09 UTC`, and a distinct
  second `POST` completed successfully at `17:09:16 UTC` after 6.207 seconds. Its database request
  timestamp is the persisted `17:09:10 UTC` value above.

The source trace confirms that Prepare is a mutation, not a read side effect. The web client sends
the Prepare request with `method: 'POST'`; `usePrepareReset` exposes that client call as an explicit
mutation; and the only production component call site is the **Prepare reset and backup** button's
`onClick`. Execute success invalidates the private Semester query and then refetches status, but
both paths call only `GET /admin/semesters/management`. The page has no mount/useEffect callback,
stale mutation callback or polling callback that invokes Prepare; StrictMode does not replay event
handlers. The API endpoint is itself `POST /reset/prepare` and is the sole production caller of
`prepare_semester_reset`.

The backend guard also behaved as designed. It serializes preparation with an advisory lock,
permits at most one `RUNNING` lifecycle operation, and reuses only the same actor/current-semester
Reset. After the first Reset completed, however, the newly created semester had no reset operation,
no USER and no active operation, so a newly requested Prepare was contractually eligible. The
immediate root cause of the anomaly is therefore the second browser-originated POST, not query
invalidation, render, polling, retry or a duplicate backend insert. Server logs cannot prove the
exact physical gesture or person that initiated the browser request, so the record does not claim
that a named operator deliberately clicked the button.

No production behavior was changed: a cooldown or automatic cancellation would alter the Semester
lifecycle contract without evidence of an automatic code defect. A focused UI regression test now
models Prepare -> Execute -> SUCCEEDED -> invalidation/refetch/render, asserts the new empty
semester can render a fresh Prepare button, and proves that `prepareReset` is not called unless that
button is clicked. The focused test passed, the full web suite passed (76 files / 718 tests), and
TypeScript, ESLint and Prettier checks passed. The non-live Semester backend management/API/reset
suite also passed (19 tests), covering the current concurrency/idempotency guard.

The final read-only reconciliation found 1 Admin; 0 USERs in the new `CURRENT` semester; and all 3
old-cohort USERs still verified on the earlier `CLOSED` semester, with 3 profiles, 13 interest
selections, 7 language selections, 14 activity selections, 2 custom preferences and 2 `ACCEPTED`
invitations. That cohort still owns 2 ACTIVE Matches, 2 conversations and 4 messages. A restored
USER session independently displayed its current Buddy and all 4 conversation messages. This
passes the post-Reset multiple-Buddy/chat-retention and Admin-reconciliation integrity check; it
does not close the separate stale-tab/type race or final restore-blocked-after-new-USER rehearsal.

There is no supported cancel/abandon endpoint or UI action for a prepared Semester operation in the
current repository. At the close of the anomaly investigation, the second operation and backup
were therefore intentionally left untouched. The only existing product-supported transition was
the separately gated destructive Execute Reset flow; it was invoked only after the new explicit
confirmation documented below.

### Second empty-current Reset completion

After the anomaly was attributed and the zero-row deletion scope was re-reviewed, the operator
gave a new explicit action-time confirmation, entered the Admin credential and exact phrase, and
executed the already-prepared second Reset. The Admin UI reported successful server completion and
refreshed to a new `CURRENT` semester with 0 student accounts, a completed latest Reset and a
`READY` protected backup.

An aggregate-only read-only database audit confirmed the authoritative result:

- the second Reset remained the same operation requested at `2026-10-04 17:09:10 UTC` and completed
  `SUCCEEDED` at `2026-10-06 06:06:33 UTC` (`13:06:33` Asia/Saigon);
- its empty source semester is now `CLOSED` with marker 0; the replacement semester started at the
  completion instant and is `CURRENT` with marker 0 and 0 persisted USER rows;
- its backup is `READY`, all database/avatar manifest locations and checksums are present,
  `verified_at` remains `2026-10-04 17:09:16 UTC`, expiry is exactly 30 days after completion at
  `2026-11-05 06:06:33 UTC`, and `restored_at` remains null;
- no Restore was prepared or executed after this Reset; the database still contains exactly one
  successful historical Restore;
- the earlier closed cohort remains intact with 1 Admin, 3/3 verified USERs, 3 profiles, 2 custom
  preferences, 2 accepted invitations, 2 ACTIVE Matches, 2 conversations and 4 messages.

No Restore preparation or execution was attempted in this milestone. The final
`restore-blocked-after-new-USER` rehearsal has a separate gate: the existing contract requires a
Restore operation to be prepared while the replacement semester is empty, then a genuinely new
verified USER is created, and only then is execution attempted and expected to fail atomically with
`RESTORE_BLOCKED_NEW_DATA` while preserving that new USER. That scenario remains pending explicit
authorization for Restore preparation and the later destructive execution attempt. Authorization
for preparation was subsequently granted and is recorded below; execution remains a separate gate.

### Final restore-blocked rehearsal — Restore prepared

The operator explicitly authorized **Prepare Restore for the block test** after the second Reset was
confirmed `SUCCEEDED`. Immediately before preparation, the Admin UI showed the replacement
`CURRENT` semester with 0 student accounts and the newest protected backup as `READY`.

The Admin preparation action created one Restore operation, shown as `RUNNING` at approximately
`2026-10-06 13:22` Asia/Saigon. The server-owned preflight showed a zero-row package: 0 student
accounts, profiles, custom preferences, invitations, Matches, conversations, messages and avatar
objects. The backup remained `READY`, and **Review and execute restore** became available.

No Restore credential, confirmation phrase or execution was submitted. The next controlled step is
for the operator to register and verify one genuinely new student account in the replacement
semester and complete its profile/type selection. Only after that new-cohort marker is verified may
the separately confirmed execution attempt proceed; it must fail with
`RESTORE_BLOCKED_NEW_DATA` without deleting, merging or overwriting the new USER.

### Final restore-blocked rehearsal — new USER pre-execution reconciliation

At `2026-10-06 10:28:15.598 UTC` (`17:28:15.598` Asia/Saigon), aggregate-only
read-only database checks confirmed that the newly registered USER belongs to the replacement
`CURRENT` semester. That semester now has exactly 1 persisted USER, its monotonic
`student_accounts_created` marker is 1, `first_student_created_at` is set, and the one USER is
verified with one matching-ready profile. The USER was created at
`2026-10-06 10:20:03.122443 UTC`, after the Restore operation was prepared at
`2026-10-06 06:22:00.426653 UTC`.

The earlier cohort remains isolated by boundary identity: exactly 3 USERs, all verified, still
belong to a `CLOSED` semester. Restore history contains exactly 2 operations: 1 historical
`SUCCEEDED`, 1 current `RUNNING`, and 0 `FAILED`. The newest operation is still the previously
prepared Restore; its backup remains `READY` with a zero-USER package, `completed_at` is null, and
no later Restore operation exists. No credential, confirmation phrase or execution was submitted.

The new USER's deployed Recommendation Results page displayed **2 of 2** candidates: Jonas and
Lukas. A separate read-only database reconciliation confirmed that both displayed candidates are
active, verified, matching-opted-in USERs whose semester status is `CLOSED`. This is attributable
live staging evidence of the previously identified cross-semester recommendation gap: candidate
discovery does not currently restrict recommendations to the requesting USER's semester. No
invitation was sent and no fix or data mutation was made. The rehearsal remains stopped at the
manual Execute Restore gate.

### Same-semester Buddy Matching isolation remediation

The live finding above was preserved as the pre-fix record. Source audit attributed it to two
missing application guards: the authoritative candidate query applied the REC-001 account,
profile, type and preference predicates but did not compare `User.semester_id`, and the atomic
invitation-send service locked and revalidated both participants without checking their semester
boundary. Accept/Match activation already rejected a different-semester pair.

Commit `5100d8b` implements the product invariant that new Buddy Matching interactions are limited
to one semester. The eligible principal now carries its persisted semester and fails closed when
that boundary is absent. The candidate query adds `candidate.semester_id == current.semester_id`
before projection/scoring, preserving its bounded deterministic order, fixed query count, scoring
weights, pagination and privacy-safe DTO. Invitation send compares the two locked persisted User
rows before profile lookup, invitation construction or transactional email enqueue; a mismatch
uses the existing sanitized `RECIPIENT_INELIGIBLE` contract. The independent same-semester checks
at Accept/Match activation remain unchanged. Historical invitation reads deliberately retain their
existing pair-scoring behavior, so the change does not hide or mutate old Matches, conversations
or messages.

Local verification passed the focused eligibility/recommendation, invitation send/API,
acceptance and BuddyMatch suite (60 tests before the final additional fail-closed query assertion;
the final modified eligibility/recommendation/invitation subset passed 29 tests). Ruff passed for
the whole API, and mypy reported no issues in 273 source files. The complete backend suite passed
when split along the pre-existing realtime-test boundary: 1,312 non-realtime tests plus all 13
chat-realtime tests, with 37 environment-gated disposable database/Redis live tests skipped. A
monolithic run exposed a Starlette TestClient WebSocket teardown `CancelledError`; a clean archived
snapshot of the preceding `HEAD` reproduced the same failure in the adjacent realtime tests, so it
is recorded as a pre-existing order-sensitive test-harness flake rather than a regression or a
hidden PASS. `git diff --check` passed.

After `5100d8b` was pushed to `origin/main` and the staging service updated, the same authenticated
new USER in the `CURRENT` semester was rechecked on Recommendation Results. The page changed from
the recorded **2 of 2** CLOSED-semester candidates to **No recommendations yet**; neither Jonas nor
Lukas was present. Incoming and sent invitation sections remained empty. No staging invitation was
sent because the automated service tests already prove rejection occurs before invitation/outbox
state, and a live send would create avoidable state.

This remediation required no migration and made no database, account, profile, invitation, Match,
chat, Reset, Restore or backup mutation. CLOSED-cohort login and existing historical Buddy/chat
behavior were not changed. The already-prepared Restore operation remains untouched at the manual
Execute Restore gate.

## Safe next acceptance sequence

Use dedicated staging data only. Start with the non-destructive boundary/type-lock/chat checks,
then Admin reconciliation and maintenance observation. Run the destructive second Semester
rehearsal last, after a new verified backup is READY and all exact user/semester IDs have been
reviewed. Never retry Restore solely because the old backup UI says it was already restored.

Close `ACCEPT-001` only when one redacted record maps every Definition-of-Done item to a deployed
commit, database revision, UTC observation, PASS/FAIL result and named owner approval. Until then,
`PROD-001` remains blocked.
