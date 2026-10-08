# ADMIN-006

**Control-plane status:** DEFERRED / POST-DEPLOY
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** `ADMIN-004`, `EVT-006`, `EVT-009`.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6137-6151

### ADMIN-006 — Create Admin Events list with editorial/time filters

**Task ID:** `ADMIN-006`
**Change:** Updated existing; **Status:** Planned; **Priority:** P0; **Phase:** 11
**Goal:** Let coordinators find and manage event content.
**Dependencies:** ADMIN-004, EVT-006, EVT-009
**Scope:** Event table, status/visibility/date filters, pagination and loading/error/empty states.

**Acceptance Criteria:**

- [ ] List includes drafts via admin API and derives phase labels correctly.
- [ ] Create/edit/recap links use authorized routes; cancelled events are distinguishable.

**Out of Scope:** Calendar grid or analytics charts.


### Legacy lines 8679-8701

#### ADMIN-006 — Admin Event list page

- **Task ID / Status:** `ADMIN-006` — **DEFERRED / POST-DEPLOYMENT**, modified existing; P0.
- **Objective:** replace `/admin/events` placeholder with an authorized, usable Event inventory.
- **Dependencies:** `ADMIN-004`, `EVT-006`, `EVT-009`.
- **Scope:** paginated table, search/status/visibility/time filters, create/edit links, loading/error/
  empty states, localized phase/status labels.
- **Non-goals:** calendar, analytics, drag ordering, registration or separate slider list.
- **Backend changes:** none beyond consuming Admin list API.
- **Frontend changes:** page, typed repository/query, private query keys, navigation replacement and
  EN/DE copy.
- **Database changes:** none.
- **Storage changes:** display existing signed thumbnail only; no upload.
- **Security requirements:** existing Admin RoleGuard plus backend authority; clear private query
  cache on logout/account switch; never persist Event/Admin data in Web Storage.
- **Acceptance Criteria / DoD:** Admin sees every editorial state with stable pagination and can
  reach create/edit; USER route access is denied; loading, API failure and true empty list differ.
- **Tests/Gates:** list/filter/pagination states, 401/403 UX, route guard, EN/DE, accessibility,
  no-store/private cache cleanup, typecheck/lint/build.
- **Staging acceptance:** current confirmed Admin account opens `/admin/events` and loads real API
  data without exposing the old placeholder.
- **Next Task:** `ADMIN-007`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1412: | ADMIN-006 | Create Admin Events list with editorial/time filters | 3 | ADMIN-004, EVT-006, EVT-009 | P0 |
- Legacy line 1413: | ADMIN-007 | Create Event form with managed cover upload | 3 | ADMIN-006, EVT-011 | P0 |
- Legacy line 1415: | ADMIN-009 | Create event publish, unpublish and cancel controls | 2 | ADMIN-006, EVT-009 | P0 |
- Legacy line 1416: | ADMIN-010 | Create event deletion with dependency-aware confirmation | 2 | ADMIN-005, ADMIN-006, EVT-009 | P0 |
- Legacy line 1417: | ADMIN-011 | Create admin event registration detail view | 2 | ADMIN-006, EVT-007 | P1 |
- Legacy line 4343: Next: ADMIN-006               Create Admin Events list with editorial/time filters [P0; Phase 11]
- Legacy line 4379: Event/Admin: **EVT-001/002/010 → EVT-003 → EVT-004/005/006 → EVT-009/011 → EVT-012/013 → ADMIN-006..010 + ADMIN-EVT-001 → EVS-001/002/004/005/006/007 → ADMIN-SLIDER-001..004 → FE-031 → FE-014B**. Existing EVS-003 has already supplied shared storage. The two tracks may proceed independently after shared auth/storage/audit; for the demo deadline, pause the Event lane after completed EVT-004 and resume it after the Matching demo slice. This is sequencing guidance, not an instruction to spawn agents.
- Legacy line 5167: matching, security or deployment credit. ADMIN-006/012/ADMIN-SLIDER-001 still need backend contracts.
- Legacy line 6157: **Dependencies:** ADMIN-006, EVT-011
- Legacy line 6187: **Dependencies:** ADMIN-006, EVT-009
- Legacy line 6202: **Dependencies:** ADMIN-005, ADMIN-006, EVT-009
- Legacy line 6552: **Dependencies:** ADMIN-006, EVT-007
- Legacy line 8502: \`EVT-005\`, \`EVT-006\`, \`EVT-009\`, \`EVT-011\`, \`EVS-005\`, \`EVS-007\`, \`ADMIN-006\`,
- Legacy line 8515:   \`ADMIN-006..009\`. No parallel \`/admin/event-sliders\` business page ships in MVP.
- Legacy line 8530:   -> ADMIN-006 -> ADMIN-007 -> ADMIN-008 -> ADMIN-009
- Legacy line 8677: - **Next Task:** \`ADMIN-006\`.
- Legacy line 8706: - **Dependencies:** \`ADMIN-006\`, \`EVT-011\`.
- Legacy line 8827: - **Dependencies:** \`EVT-005/006/009/011\`, \`EVS-005\`, \`ADMIN-006..009\`, \`FE-031\`, \`FE-014B\`.
- Legacy line 8912: 6. \`ADMIN-006\` — Admin Event list page
- Legacy line 8921:    - **Dependencies:** \`ADMIN-006\`, \`EVT-011\`.
- Legacy line 9094:    \`EVT-005 → EVT-006 → EVT-009 → EVT-011 → EVS-005 → ADMIN-006 → ADMIN-007 → ADMIN-008 →\`
