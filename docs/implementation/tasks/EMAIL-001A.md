# EMAIL-001A

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** -
**Dependencies (latest extracted):** EMAIL-001; Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6911-6921

#### EMAIL-001A — Cryptographic verification token service

- **Status:** **Done 2026-09-24.** The implementation is limited to cryptographic token value objects and transaction-safe persistence helpers; HTTP endpoints and email delivery remain in later tasks.
- **Purpose:** Isolate secure issue, digest, validate, consume and supersede behavior from transport endpoints.
- **Scope / likely files:** dedicated token service/value objects and model repository helpers; injectable UTC clock/random source for tests.
- **Dependencies / ownership:** EMAIL-001; Backend.
- **Security:** at least 32 random bytes from a CSPRNG, URL-safe encoding, purpose-separated digest, constant-safe comparison where applicable, no plaintext persistence/repr/log, 15-minute exact TTL.
- **Acceptance / DoD:** issue returns plaintext once and persists only digest/email snapshot; consume is atomic one-use; newest issue supersedes prior tokens; expired/changed-email/deleted-user tokens fail generically.
- **Tests/gates:** entropy/format, digest-not-plaintext, exact expiry, replay, supersession, concurrent consume and log-redaction tests.
- **Non-goals:** HTTP endpoints or email delivery.


## Cross-reference occurrences outside extracted headings

- Legacy line 6849: | EMAIL-001A (**Done 2026-09-24**) | Cryptographic verification token service | EMAIL-001 | High-entropy issue/digest/consume/supersede contract | Unit/property/replay tests |
- Legacy line 6851: | EMAIL-002 (**Done 2026-09-24**) | Request/resend verification | EMAIL-001A, MAIL-001, AUTH-020 | Current address only; rate-limited; old token superseded | API/rate/concurrency tests |
- Legacy line 6852: | EMAIL-003 (**Done 2026-09-24**) | Confirm verification | EMAIL-001A | One valid token atomically stamps current email | Expiry/replay/race tests |
- Legacy line 6902: - **Status:** **Done 2026-09-24.** The implementation adds persistence/schema support only; token generation, validation and consumption remain owned by \`EMAIL-001A\`.
- Legacy line 6938: - **Dependencies / ownership:** EMAIL-001A, MAIL-001, AUTH-020; Backend.
- Legacy line 6949: - **Dependencies / ownership:** EMAIL-001A; Backend + Database.
- Legacy line 8155: EMAIL-001 → EMAIL-001A
- Legacy line 8158: (EMAIL-001A + MAIL-001) → EMAIL-002
- Legacy line 8159: EMAIL-001A → EMAIL-003
- Legacy line 8204: 1. \`EMAIL-001\` first; then \`EMAIL-001A\`, \`MAIL-001\` and \`AUTH-V2-001\` as their dependencies permit.
