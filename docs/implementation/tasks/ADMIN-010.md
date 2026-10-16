# ADMIN-010

**Control-plane status:** DONE — FRONTEND AUTO-DEPLOYED / BACKEND & DATA PENDING
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
- A verified USER read directly returned Buddy Recruitment
  `b62cee68-8f9a-4206-89b7-d84b74fd4e8b` in both locales as `PUBLISHED`/`MEMBERS`, unscheduled,
  location-free, registration OFF and cover-ready. Field trip
  `0a9fe1f9-ea26-4426-bfd8-8900113de46f` remained `PUBLISHED`/`PUBLIC`, future-scheduled and
  cover-ready. This confirms `MEMBERS` as the direct anonymous eligibility failure; no Production
  Event was modified.
- Commit `ed250f52920b8bf415ea87224462cd10aa923df9` reached `origin/main`; GitHub Actions run
  `38576202814` passed Frontend and Backend. Push-triggered GitHub Deployment `7067400901` completed
  successfully in Vercel Production for the exact SHA and `www` serves `index-Bkc4hubM.js` with the
  new UI. No backend deployment or Event mutation occurred; those remain separately gated.

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
