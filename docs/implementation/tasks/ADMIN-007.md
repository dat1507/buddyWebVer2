# ADMIN-007

**Control-plane status:** DEFERRED / POST-DEPLOY
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** `ADMIN-006`, `EVT-011`.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6152-6166

### ADMIN-007 — Create Event form with managed cover upload

**Task ID:** `ADMIN-007`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 11
**Goal:** Create upcoming event content without code changes.
**Dependencies:** ADMIN-006, EVT-011
**Scope:** EN/DE fields, time/timezone, text location, category, organizer, visibility, optional HTTPS registration URL and cover upload.

**Acceptance Criteria:**

- [ ] Create draft before upload; failed upload/save remains recoverable; no manual image path entry.
- [ ] Client displays backend field errors and refuses incomplete publication.

**Out of Scope:** Bulk import or recurrence.


### Legacy lines 8702-8725

#### ADMIN-007 — Admin Event create form with poster upload

- **Task ID / Status:** `ADMIN-007` — **DEFERRED / POST-DEPLOYMENT**, modified existing; P0.
- **Objective:** let ADMIN create a database-backed Event and attach its first poster.
- **Dependencies:** `ADMIN-006`, `EVT-011`.
- **Scope:** shared EN/DE form fields, schedule/timezone/location, PUBLIC/MEMBERS visibility, DRAFT
  creation, cover upload/alt text, validation/feedback and recoverable multi-step flow.
- **Non-goals:** seed-only workflow, recurrence, registration, recap, delete or publish action.
- **Backend changes:** none beyond consuming existing Admin/media APIs.
- **Frontend changes:** reusable Event form primitives; create DRAFT first, then upload/attach poster;
  disable double submit; retain user input on recoverable error; explicit success destination.
- **Database changes:** none.
- **Storage changes:** multipart upload through backend only.
- **Security requirements:** credentials included through shared client; CSRF header; no Supabase key,
  bucket/key selector or direct SDK in browser.
- **Acceptance Criteria / DoD:** valid Event persists across refresh with correct poster; field/file
  errors are actionable; partial upload/save failure does not claim success or silently lose data;
  one click cannot create duplicates.
- **Tests/Gates:** validation boundaries, create persistence, double-submit, draft-first/upload failure/
  retry, invalid/oversize file feedback, USER denial, EN/DE and a11y/build gates.
- **Staging acceptance:** Admin creates one disposable DRAFT with poster; it does not appear publicly
  before publication.
- **Next Task:** `ADMIN-008`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1413: | ADMIN-007 | Create Event form with managed cover upload | 3 | ADMIN-006, EVT-011 | P0 |
- Legacy line 1414: | ADMIN-008 | Create Edit Event form | 2 | ADMIN-007 | P0 |
- Legacy line 4344: Next: ADMIN-007               Create Event form with managed cover upload [P0; Phase 11]
- Legacy line 6172: **Dependencies:** ADMIN-007
- Legacy line 8503: \`ADMIN-007\`, \`ADMIN-008\`, \`ADMIN-009\`, \`FE-031\`, and \`FE-014B\` are updated by the full
- Legacy line 8530:   -> ADMIN-006 -> ADMIN-007 -> ADMIN-008 -> ADMIN-009
- Legacy line 8637: - **Frontend changes:** typed media request/error contract only; form UI belongs to \`ADMIN-007/008\`.
- Legacy line 8700: - **Next Task:** \`ADMIN-007\`.
- Legacy line 8730: - **Dependencies:** \`ADMIN-007\`.
- Legacy line 8918: 7. \`ADMIN-007\` — Admin Event create form with poster upload
- Legacy line 8927:    - **Dependencies:** \`ADMIN-007\`.
- Legacy line 8967:   \`ADMIN-007\` + \`ADMIN-008\` because they intentionally share form primitives; \`FE-031\` + \`FE-014B\`
- Legacy line 9094:    \`EVT-005 → EVT-006 → EVT-009 → EVT-011 → EVS-005 → ADMIN-006 → ADMIN-007 → ADMIN-008 →\`
