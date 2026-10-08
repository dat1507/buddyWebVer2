# ADMIN-008

**Control-plane status:** DEFERRED / POST-DEPLOY
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** `ADMIN-007`.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6167-6181

### ADMIN-008 — Create Edit Event form

**Task ID:** `ADMIN-008`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 11
**Goal:** Maintain existing event content safely.
**Dependencies:** ADMIN-007
**Scope:** Reuse event fields, replace cover, optimistic version check.

**Acceptance Criteria:**

- [ ] Edit persists to API and survives reload; conflicting updates offer reload/review.
- [ ] Successful edit invalidates event and linked-slider data; no source edit or deployment is necessary.

**Out of Scope:** Different form schema or copied hard-coded events.


### Legacy lines 8726-8747

#### ADMIN-008 — Admin Event edit and poster replacement form

- **Task ID / Status:** `ADMIN-008` — **DEFERRED / POST-DEPLOYMENT**, modified existing; P0.
- **Objective:** edit canonical Event content and replace its poster without code/deployment changes.
- **Dependencies:** `ADMIN-007`.
- **Scope:** preload by ID, reuse form, optimistic version, save feedback, poster preview/replacement,
  conflict recovery and unsaved-change protection.
- **Non-goals:** separate slider fields, bulk editor, history UI or delete.
- **Backend changes:** none beyond consuming update/media APIs.
- **Frontend changes:** edit route/page, mutation sequencing, query invalidation for Admin/public Event
  and slider keys, conflict reload/review UX.
- **Database changes:** none.
- **Storage changes:** invoke failure-safe replacement; never reuse/overwrite old object key.
- **Security requirements:** RoleGuard + backend ADMIN/CSRF; sanitized errors; clear selected file after
  terminal result without clearing unrelated form data.
- **Acceptance Criteria / DoD:** title/description/time/location/poster changes survive refresh;
  stale update never overwrites silently; success/error are explicit; public caches are invalidated.
- **Tests/Gates:** prefill/save/reload, version 409, poster replace/cleanup-pending, retry and double
  submit, navigation with dirty form, EN/DE/a11y/type/build.
- **Staging acceptance:** Admin changes the disposable Event and sees the persisted values after F5.
- **Next Task:** `ADMIN-009`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1414: | ADMIN-008 | Create Edit Event form | 2 | ADMIN-007 | P0 |
- Legacy line 1420: | ADMIN-EVT-001 | Create recap editor and publish controls | 2 | ADMIN-008, EVT-013 | P0 |
- Legacy line 4345: Next: ADMIN-008               Create Edit Event form [P0; Phase 11]
- Legacy line 6217: **Dependencies:** ADMIN-008, EVT-013
- Legacy line 8503: \`ADMIN-007\`, \`ADMIN-008\`, \`ADMIN-009\`, \`FE-031\`, and \`FE-014B\` are updated by the full
- Legacy line 8530:   -> ADMIN-006 -> ADMIN-007 -> ADMIN-008 -> ADMIN-009
- Legacy line 8724: - **Next Task:** \`ADMIN-008\`.
- Legacy line 8753: - **Dependencies:** \`ADMIN-008\`, \`EVT-009\`.
- Legacy line 8924: 8. \`ADMIN-008\` — Admin Event edit and poster replacement
- Legacy line 8933:    - **Dependencies:** \`ADMIN-008\`, \`EVT-009\`.
- Legacy line 8967:   \`ADMIN-007\` + \`ADMIN-008\` because they intentionally share form primitives; \`FE-031\` + \`FE-014B\`
- Legacy line 9094:    \`EVT-005 → EVT-006 → EVT-009 → EVT-011 → EVS-005 → ADMIN-006 → ADMIN-007 → ADMIN-008 →\`
