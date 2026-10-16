# ACCOUNT-DELETE-001 — Production account removal

**Status:** DONE — PRODUCTION VERIFIED
**Completed:** 2026-10-17 (Asia/Saigon)
**Track:** release-operations

## Objective

Remove one owner-specified Production account so its normalized email can be registered again,
including owned profile, Buddy relationship, session, verification and private-image state, while
preserving unrelated users, shared resources and retained operational history.

## Verified architecture and scope

- Registration and login use the backend-owned `app_private.users` password/JWT system. No matching
  Supabase Auth row existed.
- The target was exactly one USER with one profile, invitation, ACTIVE Match, Buddy conversation,
  refresh session, verification token and private profile image.
- The conversation had no messages and the account had no Event registration.
- Audit, Event ownership/media and Semester operation/backup `RESTRICT` dependencies were all zero.
- Two outbox rows were already sent and are retained by the existing `ON DELETE SET NULL` policy.

## Execution and acceptance

After explicit owner confirmation, one guarded transaction locked and revalidated the exact user,
aborted on identity/count/blocker drift, and deleted exactly one `app_private.users` row. Existing
cascades removed account-owned profile/preferences, invitation, Match, conversation, session and
verification data. The private profile image object was then deleted through Supabase Storage.

Post-checks found zero target application/Auth/profile/Match/invitation/conversation/session/token/
registration/Storage records. The other Buddy participant and profile remain present. Retained
outbox rows have null user references, the normalized email is available, and Production readiness
remains healthy. No replacement account was created.

## Change boundary

No application source, schema, migration, constraint, trigger, provider configuration, secret,
commit, push or deployment changed. Evidence is sanitized in
`docs/operations/account-delete-001-production-2026-10-17.md`.
