# EMAIL-002

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** -
**Dependencies (latest extracted):** EMAIL-001A, MAIL-001, AUTH-020; Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6933-6943

#### EMAIL-002 — Request and resend verification

- **Status:** **Done 2026-09-24.** The authenticated USER endpoint now stages the newest digest-only token and a durable current-address outbox event atomically; AES-GCM sealed delivery payloads keep the plaintext token out of persistence while preserving worker retries.
- **Purpose:** Issue a safe 15-minute link to the current address.
- **Scope / likely files:** auth router/schema/service, rate-limit policy, verification email template/outbox event, environment base URL.
- **Dependencies / ownership:** EMAIL-001A, MAIL-001, AUTH-020; Backend.
- **Security:** authenticated current USER, CSRF, per-user/IP rate limits, generic response, supersede old tokens, allowlisted HTTPS base URL.
- **Acceptance / DoD:** first request and resend create at most one usable latest token and post-commit email event; already-verified behavior is explicit/idempotent; raw token never persists or logs.
- **Tests/gates:** API, CSRF, rate, expiry, resend concurrency, outbox and sanitized-log tests.
- **Non-goals:** verifying the token or changing email.


## Cross-reference occurrences outside extracted headings

- Legacy line 6851: | EMAIL-002 (**Done 2026-09-24**) | Request/resend verification | EMAIL-001A, MAIL-001, AUTH-020 | Current address only; rate-limited; old token superseded | API/rate/concurrency tests |
- Legacy line 6853: | EMAIL-004 (**Done 2026-09-24**) | Change email + reverify | EMAIL-001, EMAIL-002 | Unique new email; clears verification; data retained | Auth/CSRF/session/data tests |
- Legacy line 6854: | EMAIL-005 (**Done 2026-09-24**) | Verification/change-email UX | EMAIL-002..004, AUTH-021 | Accurate Verified/Unverified UX and safe links | Component/integration/a11y tests |
- Legacy line 6971: - **Dependencies / ownership:** EMAIL-002..004, AUTH-021; Frontend.
- Legacy line 8158: (EMAIL-001A + MAIL-001) → EMAIL-002
- Legacy line 8160: (EMAIL-001 + EMAIL-002) → EMAIL-004
- Legacy line 8161: (EMAIL-002 + EMAIL-003 + EMAIL-004) → EMAIL-005
- Legacy line 8205: 2. \`EMAIL-002..005\`, \`OPS-001..003\`, \`PREF-001..004\` and \`REC-001..003\` are complete. Proceed with
- Legacy line 8215: - PREF-001/002/003 can run alongside EMAIL-001/001A/MAIL-001/EMAIL-002.
