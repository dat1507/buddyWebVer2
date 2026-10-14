# ADMIN-010

**Control-plane status:** IMPLEMENTED / FULL REGRESSION PASS — COMMIT PENDING
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-005, ADMIN-006, EVT-009

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Implementation evidence — 2026-10-14

- Production anonymous EN/DE reads return only Field trip. Field trip is confirmed
  `PUBLISHED`/`PUBLIC`, future-scheduled and cover-ready. Buddy Recruitment is absent from both the
  public list and Slider, so exclusion happens at the canonical public eligibility boundary before
  frontend rendering.
- Source inspection identified the Admin creation defect: the Audience input had been hidden while
  new drafts still defaulted to `MEMBERS`. An Admin could therefore publish a new Event without any
  visible way to make it `PUBLIC`. New drafts now default to `PUBLIC`, and the Audience control is
  restored so existing member-only Events can be corrected explicitly without weakening backend
  visibility enforcement.
- The canonical Slider query already accepts cover-ready unscheduled announcements on current
  `main`. A regression now proves Field trip and an unscheduled Buddy Recruitment project together
  in both English and German. Draft, member-only, deleted, past and missing/non-ready-cover rows
  remain excluded by the existing predicates.
- Admin Inventory now exposes a destructive Delete action with an Event-named confirmation dialog,
  cancel path, pending lock, safe error/success feedback and Admin/public query invalidation after
  success. The UI consumes the existing versioned `DELETE /api/admin/events/:id` contract.
- Backend policy remains unchanged: persisted ADMIN RBAC and CSRF are mandatory; stale versions,
  active registrations and published recaps return conflicts; the audit write shares the deletion
  transaction; only Event-owned media object keys are scheduled for post-commit cleanup. Event
  media ownership and unique object keys prevent shared cover deletion.
- Focused verification: 48 backend Event/API tests and 41 frontend Admin/Slider tests PASS. Full
  verification: backend 1,414 PASS / 37 explicit live skips; frontend 86 files / 803 tests PASS;
  Ruff, strict mypy (107 files), TypeScript, ESLint, Prettier and the Admin-ON/Public-ON Production
  build PASS. The existing bundle-size advisory is unchanged.
- Exact persisted Admin fields for Buddy Recruitment were not independently read because available
  browser sessions were anonymous or USER-only. The owner must authenticate the already-open Admin
  Login before that data comparison can be upgraded from source/API-supported inference to direct
  record evidence. No Production Event was modified.

## Preserved contract sections

### Legacy lines 6197-6211

### ADMIN-010 — Create event deletion with dependency-aware confirmation

**Task ID:** `ADMIN-010`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 11
**Goal:** Delete eligible content without leaving broken relationships.
**Dependencies:** ADMIN-005, ADMIN-006, EVT-009
**Scope:** Confirm dialog and API dependency/conflict feedback.

**Acceptance Criteria:**

- [ ] Blocking registrations/published recap are explained; 409 leaves UI record intact.
- [ ] Successful deletion refreshes lists and linked sliders; users never type filesystem paths.

**Out of Scope:** Bulk destructive deletion.


## Cross-reference occurrences outside extracted headings

- Legacy line 1416: | ADMIN-010 | Create event deletion with dependency-aware confirmation | 2 | ADMIN-005, ADMIN-006, EVT-009 | P0 |
- Legacy line 1444: | FE-014B | Verify live Event Slider integration and linked Event freshness | 2 | FE-014, EVS-007, ADMIN-SLIDER-004, ADMIN-010, FE-031 | P0 |
- Legacy line 4347: Next: ADMIN-010               Create event deletion with dependency-aware confirmation [P0; Phase 11]
- Legacy line 5192: This keeps ADMIN-010 and ADMIN-SLIDER-003 domain policy outside the primitive while allowing them to
- Legacy line 6247: **Dependencies:** FE-014, EVS-007, ADMIN-SLIDER-004, ADMIN-010, FE-031
- Legacy line 8448:   retryable and must not resurrect the Event. \`ADMIN-010\` UI remains optional follow-up even though
- Legacy line 8517: \`EVT-007\`, \`EVT-012\`, \`EVT-013\`, \`ADMIN-010\`, \`ADMIN-011\`, \`ADMIN-EVT-001/002\`, \`FE-030\`,
- Legacy line 8986: - **Delete Event UI:** backend service/delete contract is preserved; \`ADMIN-010\` remains optional
