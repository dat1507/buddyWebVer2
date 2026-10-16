# ACCOUNT-DELETE-001 Production evidence — 2026-10-17

This record intentionally omits the personal email, private Storage key and unrelated participant
identifiers. The owner received the target application/profile identifiers directly in chat.

## Authorization and preflight

- The owner requested deletion, received the exact read-only scope and then explicitly confirmed
  destructive execution.
- Production contained exactly one normalized application account and no matching Supabase Auth
  row.
- Direct FK inspection confirmed the expected `CASCADE`, `SET NULL` and `RESTRICT` policies. No
  constraint or trigger was changed or disabled.
- There were zero blocking audit, Event/media or Semester references and no active Semester
  operation. The write-barrier trigger remained enabled.

## Executed scope

- A bounded transaction locked and revalidated the exact USER, profile, Match and zero-blocker
  assumptions, then deleted exactly one application user.
- Existing cascades removed one profile, one accepted invitation, one ACTIVE Match, one Buddy
  conversation, one refresh session, one verification token, photo metadata and owned preference
  rows. No Buddy message or Event registration existed.
- One private profile-image object was deleted through the Supabase Storage UI; the success result
  was followed by a direct `storage.objects` zero-count check.
- Two already-sent transactional-outbox rows were retained; their user reference is null under the
  existing schema policy.

## Post-deletion verification

- Target application user, Auth user, profile, invitation, Match, conversation, session, token,
  registration, profile metadata/preferences and Storage object: zero.
- Other Buddy participant and profile: present.
- Normalized email availability: true.
- Production readiness: `ready`; database and Redis `ok`; email and Storage `configured`.
- No replacement registration, test message, Event/shared-resource mutation, schema/configuration
  change, commit, push or deployment occurred.

Result: **SUCCESS — PRODUCTION VERIFIED**.
