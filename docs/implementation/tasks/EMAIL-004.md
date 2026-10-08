# EMAIL-004

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** -
**Dependencies (latest extracted):** EMAIL-001/002, existing sessions; Backend + Database.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6955-6965

#### EMAIL-004 — Authenticated email change and re-verification

- **Status:** **Done 2026-09-24.** The current-password and CSRF-protected USER endpoint atomically replaces the unique canonical address, clears timestamp verification, supersedes the prior token, and enqueues verification to the replacement address while retaining sessions and User-owned data.
- **Purpose:** Let a USER replace the login email without losing Buddy data.
- **Scope / likely files:** auth schema/router/service, session projection and docs; update canonical email, clear timestamp, revoke tokens and enqueue verification.
- **Dependencies / ownership:** EMAIL-001/002, existing sessions; Backend + Database.
- **Security:** CSRF plus current-password or recent step-up verification, uniqueness protection, generic conflict, session policy explicitly tested.
- **Acceptance / DoD:** verified or unverified USER can change to a valid unique address; verification clears atomically; invitations/Matches/chat remain; protected interactions lock immediately; notifications target only the verified current address.
- **Tests/gates:** auth/CSRF, uniqueness/race, session reload, data-retention and re-unlock integration tests.
- **Non-goals:** merging accounts or forwarding old-address mail.


## Cross-reference occurrences outside extracted headings

- Legacy line 6853: | EMAIL-004 (**Done 2026-09-24**) | Change email + reverify | EMAIL-001, EMAIL-002 | Unique new email; clears verification; data retained | Auth/CSRF/session/data tests |
- Legacy line 8160: (EMAIL-001 + EMAIL-002) → EMAIL-004
- Legacy line 8161: (EMAIL-002 + EMAIL-003 + EMAIL-004) → EMAIL-005
