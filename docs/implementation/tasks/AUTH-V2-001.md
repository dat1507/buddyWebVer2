# AUTH-V2-001

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** -
**Dependencies (latest extracted):** EMAIL-001, BE-016; Backend contract + Frontend integration.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6977-6987

#### AUTH-V2-001 — Shared VERIFIED Buddy capability guard

- **Status:** **Done 2026-09-24.** The implementation adds one current-database USER/profile capability policy, reusable HTTP and WebSocket dependencies, the `EMAIL_VERIFICATION_REQUIRED` completion reason and its frontend parser/localization. Later Buddy/chat tasks remain responsible for attaching the guard to their own transports and resource queries.
- **Purpose:** Enforce the UNVERIFIED lock once for all Buddy/chat transports.
- **Scope / likely files:** backend dependencies/policies, completion reason schema/service and frontend reason parser.
- **Dependencies / ownership:** EMAIL-001, BE-016; Backend contract + Frontend integration.
- **Security:** current database timestamp, role/account state and profile ownership; never trust JWT/client verification fields alone.
- **Acceptance / DoD:** UNVERIFIED users cannot be recommended, receive new invitations, list/interact with invitations/Buddies, or read/send chat; preserved records unlock after reverify if still valid.
- **Tests/gates:** endpoint permission matrix plus WebSocket dependency tests; no protected query executes before guard.
- **Non-goals:** deleting or expiring preserved data on email change.


## Cross-reference occurrences outside extracted headings

- Legacy line 6707: | Email identity | **Implemented; deployed verification acceptance passed** | \`0008_email_verification.py\`, \`models/user.py\`, \`models/email_verification.py\`, \`services/email_verification*.py\`, auth APIs and frontend verification/email-change UX implement nullable \`email_verified_at\`, digest-only one-use tokens, 15-minute expiry, resend and change-email re-verification | Reuse unchanged. \`EMAIL-001..005\` and \`AUTH-V2-001\` are code-complete; OPS-002 proved request → outbox → Cron → Edge → Resend → confirm-once → generic replay rejection. ADMIN login/RBAC remains independent from the USER verification timestamp. |
- Legacy line 6855: | AUTH-V2-001 (**Done 2026-09-24**) | Shared VERIFIED capability guard | EMAIL-001, BE-016 | Backend locks all Buddy/chat actions and candidacy | Dependency/matrix tests |
- Legacy line 6860: | REC-001 (**Done 2026-09-27**) | V2 eligibility + safe DTO | AUTH-V2-001, PREF-003 | Opposite type, complete/opted-in/verified; no reservation | Policy/privacy tests |
- Legacy line 6879: | CHAT-002 (**Done 2026-10-01**) | History/read/retention service | CHAT-001, AUTH-V2-001 | Participant-only cursor history; idempotent send; atomic first-read retention formula | API/time/auth/PostgreSQL race tests |
- Legacy line 7115: - **Dependencies / ownership:** AUTH-V2-001, PREF-003; Backend.
- Legacy line 7161: - **Dependencies / ownership:** REC-002, AUTH-V2-001; Backend.
- Legacy line 7411: - **Dependencies / ownership:** INV-002, REC-002, AUTH-V2-001; Backend.
- Legacy line 7576: - **Dependencies / ownership:** BUDDY-001, INV-005, AUTH-V2-001; Backend.
- Legacy line 7706: - **Dependencies / ownership:** CHAT-001, AUTH-V2-001; Backend.
- Legacy line 8157: EMAIL-001 → AUTH-V2-001
- Legacy line 8165: (AUTH-V2-001 + PREF-003) → REC-001 → REC-002 → REC-003
- Legacy line 8172: (INV-002 + REC-002 + AUTH-V2-001) → INV-004
- Legacy line 8180: (CHAT-001 + AUTH-V2-001) → CHAT-002
- Legacy line 8204: 1. \`EMAIL-001\` first; then \`EMAIL-001A\`, \`MAIL-001\` and \`AUTH-V2-001\` as their dependencies permit.
