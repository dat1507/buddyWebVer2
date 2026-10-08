# ADMIN-V2-002

**Control-plane status:** DONE / PRESERVED
**Track:** admin
**Priority:** -
**Dependencies (latest extracted):** ADMIN-V2-001, ADMIN-003/004; Frontend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7811-7840

#### ADMIN-V2-002 — Monitoring-only Admin Matching UI

- **Status:** **DONE 2026-10-02.** `/admin/matching` now replaces the placeholder with a responsive,
  localized read-only monitoring page. Independent private queries load aggregate participant,
  verification, ACTIVE Match, zero-Buddy and effective invitation-state totals in parallel with the
  bounded participant page. The table delegates page/page-size and only the backend-supported
  `student_type`, `verified` and `zero_buddies_only` filters to ADMIN-V2-001. Audited participant
  detail renders only the matching-safe current profile, preferences, availability and operational
  flags. Loading, updating, empty, sanitized error/retry and end-of-page states are explicit.
- **Security / privacy:** the route reuses the authoritative ADMIN guard; USER access is denied before
  a monitoring query runs. Strict response schemas reject extra/internal fields. Every query is
  marked private under the session-cleared cache namespace; logout and account/role changes remove
  it. No Run, Preview, Publish, Override, invitation, matching or other mutation control/route was
  introduced, and no email, User/auth/session/message/storage data is rendered.
- **Verification:** dedicated API-contract/page/DataTable tests passed (`30 passed`); the relevant
  Admin/auth/layout regression set passed (`106 passed`). The full frontend suite passed
  (`669 passed`, 68 files, two workers) after an unrelated avatar timing test that failed once under
  the first high-concurrency run passed alone and in the final full run. Prettier, ESLint, strict
  TypeScript, production build and production dependency audit (zero vulnerabilities) passed.
  Browser smoke confirmed the local deep link loads and unauthenticated access redirects to
  `/adminLogin`; authenticated browser data-view acceptance was not claimed because no provisioned
  ADMIN browser session/credentials were available. No backend or database change was required.
- **Purpose:** Replace placeholder/old controls with accurate monitoring.
- **Scope / likely files:** `/admin/matching` page, stats/cards/tables/filters/locales using existing AdminLayout/DataTable.
- **Dependencies / ownership:** ADMIN-V2-001, ADMIN-003/004; Frontend.
- **Security:** no mutation controls; safe DTO only; private cache/session handling.
- **Acceptance / DoD:** participant/verification/invitation/ACTIVE/Buddy-count/zero-Buddy states render with loading/empty/error; old Run/Preview/Publish/Override controls are absent from UI and routes.
- **Tests/gates:** component/a11y, role integration and explicit absence tests for superseded controls.
- **Non-goals:** research algorithm dashboard or individual matching actions.


## Cross-reference occurrences outside extracted headings

- Legacy line 6711: | Matching frontend | **REC-004, INV-007, BUDDY-003, CHAT-004 and ADMIN-V2-002 implemented** | \`/user/matching\` consumes the strict privacy-safe recommendation, invitation and Current Buddies contracts; \`/user/buddy?conversation=<UUID>\` uses the authorized text-chat UI; \`/admin/matching\` now provides read-only aggregate, participant and safe-detail monitoring over the ADMIN-V2-001 APIs. | Reuse these sections unchanged in Semester work; neither the chat nor Admin UI creates or mutates a Buddy relationship or invitation. |
- Legacy line 6884: | ADMIN-V2-002 (**Done 2026-10-02**) | Monitoring UI | ADMIN-V2-001, ADMIN-003/004 | No run/publish/override controls | UI/RBAC/a11y tests |
- Legacy line 8184: (INV-006 + BUDDY-002) → ADMIN-V2-001 → ADMIN-V2-002
- Legacy line 8196: All functional branches + CHAT-005 + ADMIN-V2-002 + SEM-007 + OPS-003
- Legacy line 8224: Final integration convergence: EMAIL-005 + PREF-004 + PROFILE-V2-002 + REC-004 + INV-007/008/009 + BUDDY-003 + CHAT-004/005 + ADMIN-V2-002 + SEM-007 + OPS-003 must all pass before ACCEPT-001.
- Legacy line 8244: The **second mandatory staging milestone** is after the complete user vertical slice **through PROFILE-V2-002 and CHAT-004 plus INV-008/009 and ADMIN-V2-002**. It validates two real verified users from recommendation through invitation/email/Accept/Current Buddies/chat, including exact invitation boundaries and the post-Accept type lock. Staging remains incomplete until **SEM-007 + CHAT-005 + OPS-003** and ACCEPT-001 prove reset/backup/restore/blocking and retention.
- Legacy line 8294: | **STAGING** | **OPS-002 AND OPS-003 DONE** | Early infrastructure, restore/migration, Edge/Cron A–F, real verification acceptance and primary/backup alert routing passed. The implemented PROFILE-V2-002 + CHAT-004 + INV-008/009 + ADMIN-V2-002 vertical slice still needs staging acceptance; release-candidate staging requires SEM-007 and ACCEPT-001. |
