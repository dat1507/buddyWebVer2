# ADMIN-009

**Control-plane status:** IMPLEMENTED / AUTOMATED PASS — STAGING UI GATE PENDING
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** `ADMIN-008`, `EVT-009`.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Implementation evidence — 2026-10-09

- Added explicit publish/move-to-draft/cancel controls, localized readiness gaps, destructive
  confirmation, duplicate-submit locking, conflict handling and private/public query invalidation.
- No manual Complete action exists; 15 focused Admin API/editor tests pass.

## Preserved contract sections

### Legacy lines 6182-6196

### ADMIN-009 — Create event publish, unpublish and cancel controls

**Task ID:** `ADMIN-009`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 11
**Goal:** Expose editorial actions separately from the clock.
**Dependencies:** ADMIN-006, EVT-009
**Scope:** DRAFT/PUBLISHED/CANCELLED controls; display derived temporal phase.

**Acceptance Criteria:**

- [ ] No manual Complete action; publication checks show actionable missing fields.
- [ ] Cancellation remains visible to intended audience, disables registration, and unpublishing hides linked public promotion.

**Out of Scope:** Automated emails or notifications.


### Legacy lines 8748-8772

#### ADMIN-009 — Event publish/unpublish/cancel controls

- **Task ID / Status:** `ADMIN-009` — **DEFERRED / POST-DEPLOYMENT**, modified existing; P0.
- **Objective:** provide the minimal editorial action that controls whether an Event can appear
  publicly while preserving the implemented status model.
- **Dependencies:** `ADMIN-008`, `EVT-009`.
- **Scope:** DRAFT/PUBLISHED/CANCELLED actions, publication-readiness feedback, confirmation for
  hiding/cancelling, pending/error/success states and public query invalidation.
- **Non-goals:** active boolean, visibility windows, scheduled publish, manual complete or notification
  email.
- **Backend changes:** none beyond status API.
- **Frontend changes:** status controls with disabled duplicate action and localized explanations.
- **Database changes:** none.
- **Storage changes:** publication requires valid attached ready cover; no object mutation.
- **Security requirements:** ADMIN/CSRF enforced by API; UI state is never authority; no optimistic
  public-success claim before server response.
- **Acceptance Criteria / DoD:** publish rejects incomplete Event clearly; successful publish makes a
  PUBLIC upcoming Event eligible for slider/detail; unpublish/cancel removes it from slider; reload
  reflects server state.
- **Tests/Gates:** each transition, incomplete validation, 401/403/CSRF, repeated click, cache
  invalidation, EN/DE/a11y/build.
- **Staging acceptance:** publish the disposable Event with the current Admin account and verify the
  API eligibility before public browser acceptance.
- **Next Task:** `FE-031`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1415: | ADMIN-009 | Create event publish, unpublish and cancel controls | 2 | ADMIN-006, EVT-009 | P0 |
- Legacy line 4346: Next: ADMIN-009               Create event publish, unpublish and cancel controls [P0; Phase 11]
- Legacy line 8503: \`ADMIN-007\`, \`ADMIN-008\`, \`ADMIN-009\`, \`FE-031\`, and \`FE-014B\` are updated by the full
- Legacy line 8530:   -> ADMIN-006 -> ADMIN-007 -> ADMIN-008 -> ADMIN-009
- Legacy line 8746: - **Next Task:** \`ADMIN-009\`.
- Legacy line 8801: - **Dependencies:** \`FE-014\`, \`EVS-005\`, \`FE-031\`, \`ADMIN-009\`.
- Legacy line 8930: 9. \`ADMIN-009\` — Event publish/unpublish/cancel controls
- Legacy line 8946:     - **Dependencies:** \`EVS-005\`, \`FE-031\`, \`ADMIN-009\`.
- Legacy line 8979: - **Admin browser points:** a local authenticated smoke follows \`ADMIN-009\`; the real deployed Admin
- Legacy line 9095:    \`ADMIN-009 → FE-031 → FE-014B → EVS-007 → ACCEPT-EVENT-001\`.
