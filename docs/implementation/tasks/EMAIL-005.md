# EMAIL-005

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** -
**Dependencies (latest extracted):** EMAIL-002..004, AUTH-021; Frontend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6966-6976

#### EMAIL-005 — Verified/Unverified and email-change UX

- **Status:** **Done 2026-09-24.** The frontend now preserves the timestamp-backed session projection, exposes verified/unverified state on profile/settings, supports resend and current-password email change, and confirms opaque URL tokens without persistence before refreshing `/auth/me` and using the fixed `/user` return path.
- **Purpose:** Expose the backend state and safe recovery actions.
- **Scope / likely files:** session parser, profile/settings pages, auth client, locale strings, confirmation route/page and tests.
- **Dependencies / ownership:** EMAIL-002..004, AUTH-021; Frontend.
- **Security:** no token persistence/analytics; safe internal return path; do not infer verification from a sent email.
- **Acceptance / DoD:** status survives refresh/login; Verify/Resend handles throttle/expiry; email change immediately shows locked state; successful confirm refreshes session state.
- **Tests/gates:** component/integration, EN/DE, keyboard/screen-reader, reload and safe-link tests.
- **Non-goals:** Buddy feature implementation.


## Cross-reference occurrences outside extracted headings

- Legacy line 6854: | EMAIL-005 (**Done 2026-09-24**) | Verification/change-email UX | EMAIL-002..004, AUTH-021 | Accurate Verified/Unverified UX and safe links | Component/integration/a11y tests |
- Legacy line 6863: | REC-004 (**Done 2026-09-27**) | Read-only Recommended Buddies UI | REC-003, EMAIL-005 | Cards/explanation/profile/preferences/availability plus locked/loading/empty/error/pagination states; no invitation action | UI/a11y/contract tests |
- Legacy line 7100: **REC-004 handoff:** Completed below after its declared \`REC-003\` and \`EMAIL-005\` dependencies.
- Legacy line 7172: - **Dependencies / ownership:** REC-003, EMAIL-005; Frontend.
- Legacy line 8161: (EMAIL-002 + EMAIL-003 + EMAIL-004) → EMAIL-005
- Legacy line 8166: (REC-003 + EMAIL-005) → REC-004
- Legacy line 8216: - EMAIL-005 and PREF-004 can use contract fixtures after API schemas stabilize.
- Legacy line 8224: Final integration convergence: EMAIL-005 + PREF-004 + PROFILE-V2-002 + REC-004 + INV-007/008/009 + BUDDY-003 + CHAT-004/005 + ADMIN-V2-002 + SEM-007 + OPS-003 must all pass before ACCEPT-001.
