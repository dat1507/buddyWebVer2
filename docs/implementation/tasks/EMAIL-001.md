# EMAIL-001

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** -
**Dependencies (latest extracted):** AUTH-008/009; Backend + Database.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6900-6910

#### EMAIL-001 — Verification persistence and token model

- **Status:** **Done 2026-09-24.** The implementation adds persistence/schema support only; token generation, validation and consumption remain owned by `EMAIL-001A`.
- **Purpose:** Make the current verified email a timestamp-backed server fact.
- **Scope / likely files:** `models/user.py`, new verification model, model exports, schemas and one Alembic revision. Audit result: the legacy boolean is written as false by USER registration and true by trusted CLI ADMIN bootstrap; admin list/detail only reads it, and no verification event timestamp is recorded. Therefore migrate every legacy USER to `email_verified_at=NULL` unless operators supply a separate authoritative timestamp source. Never convert `email_verified=true` into a fabricated timestamp. Handle ADMIN separately: keep current bootstrap/login/RBAC usable and independent of student verification; an ADMIN with no trustworthy timestamp may remain NULL.
- **Dependencies / ownership:** AUTH-008/009; Backend + Database.
- **Security:** verification status is evidence-based. Account creation, last login, profile update, activity history and the unaudited legacy boolean are forbidden timestamp sources. Use high-entropy tokens, digest only, no token repr/log/audit, 15-minute expiry, one use, email snapshot and supersession.
- **Acceptance / DoD:** `email_verified_at` is nullable and authoritative for USER Buddy access; every legacy USER without an authoritative imported timestamp is UNVERIFIED after migration; ADMIN can still authenticate and use RBAC without a synthetic timestamp; constraints/indexes support one current usable token; downgrade/recovery and any evidence-import mechanism are documented; generated schema and docs agree.
- **Tests/gates:** disposable PostgreSQL upgrade fixtures cover legacy USER false, legacy USER true and ADMIN true/false; both USER booleans become NULL absent evidence; no created/login/profile/activity timestamp is copied; an explicit authoritative timestamp fixture is preserved/imported; ADMIN login/RBAC regression passes; downgrade, expiry and secret-redaction tests pass.
- **Non-goals:** sending email, UI, matching unlock.


## Cross-reference occurrences outside extracted headings

- Legacy line 6707: | Email identity | **Implemented; deployed verification acceptance passed** | \`0008_email_verification.py\`, \`models/user.py\`, \`models/email_verification.py\`, \`services/email_verification*.py\`, auth APIs and frontend verification/email-change UX implement nullable \`email_verified_at\`, digest-only one-use tokens, 15-minute expiry, resend and change-email re-verification | Reuse unchanged. \`EMAIL-001..005\` and \`AUTH-V2-001\` are code-complete; OPS-002 proved request → outbox → Cron → Edge → Resend → confirm-once → generic replay rejection. ADMIN login/RBAC remains independent from the USER verification timestamp. |
- Legacy line 6848: | EMAIL-001 (**Done 2026-09-24**) | Verification persistence + legacy migration | AUTH-008/009 | Legacy USER→NULL absent evidence; ADMIN access preserved; digest-only one-use 15m token persistence | Migration/model/Admin-regression/security tests |
- Legacy line 6849: | EMAIL-001A (**Done 2026-09-24**) | Cryptographic verification token service | EMAIL-001 | High-entropy issue/digest/consume/supersede contract | Unit/property/replay tests |
- Legacy line 6850: | MAIL-001 (**Done 2026-09-24**) | Provider + transactional outbox | BE-004, EMAIL-001 | Commit independent of delivery; retry/idempotency | Fake-provider/lease/failure tests |
- Legacy line 6853: | EMAIL-004 (**Done 2026-09-24**) | Change email + reverify | EMAIL-001, EMAIL-002 | Unique new email; clears verification; data retained | Auth/CSRF/session/data tests |
- Legacy line 6855: | AUTH-V2-001 (**Done 2026-09-24**) | Shared VERIFIED capability guard | EMAIL-001, BE-016 | Backend locks all Buddy/chat actions and candidacy | Dependency/matrix tests |
- Legacy line 6916: - **Dependencies / ownership:** EMAIL-001; Backend.
- Legacy line 6927: - **Dependencies / ownership:** BE-004, EMAIL-001; Backend + Database + Infrastructure.
- Legacy line 6960: - **Dependencies / ownership:** EMAIL-001/002, existing sessions; Backend + Database.
- Legacy line 6982: - **Dependencies / ownership:** EMAIL-001, BE-016; Backend contract + Frontend integration.
- Legacy line 8155: EMAIL-001 → EMAIL-001A
- Legacy line 8156: EMAIL-001 → MAIL-001
- Legacy line 8157: EMAIL-001 → AUTH-V2-001
- Legacy line 8160: (EMAIL-001 + EMAIL-002) → EMAIL-004
- Legacy line 8204: 1. \`EMAIL-001\` first; then \`EMAIL-001A\`, \`MAIL-001\` and \`AUTH-V2-001\` as their dependencies permit.
- Legacy line 8215: - PREF-001/002/003 can run alongside EMAIL-001/001A/MAIL-001/EMAIL-002.
