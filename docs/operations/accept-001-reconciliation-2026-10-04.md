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

## Safe next acceptance sequence

Use dedicated staging data only. Start with the non-destructive boundary/type-lock/chat checks,
then Admin reconciliation and maintenance observation. Run the destructive second Semester
rehearsal last, after a new verified backup is READY and all exact user/semester IDs have been
reviewed. Never retry Restore solely because the old backup UI says it was already restored.

Close `ACCEPT-001` only when one redacted record maps every Definition-of-Done item to a deployed
commit, database revision, UTC observation, PASS/FAIL result and named owner approval. Until then,
`PROD-001` remains blocked.
