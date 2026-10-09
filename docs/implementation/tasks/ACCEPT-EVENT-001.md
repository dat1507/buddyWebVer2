# ACCEPT-EVENT-001

**Control-plane status:** NOT READY — AWAITS EVS-007 CLOSURE AND DEPLOYED STAGING SHA
**Track:** release-operations
**Priority:** -
**Dependencies (latest extracted):** `EVS-007`, deployed matching frontend/API SHA, migration/head verification,

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 8847-8875

#### ACCEPT-EVENT-001 — Real Admin and public staging acceptance

- **Task ID / Status:** `ACCEPT-EVENT-001` — **DEFERRED / POST-DEPLOYMENT**, new; P0 release gate.
- **Objective:** prove the exact product-owner flow on the deployed staging stack before production
  Event opt-in.
- **Dependencies:** `EVS-007`, deployed matching frontend/API SHA, migration/head verification,
  private `event-media` readiness, current ADMIN account.
- **Scope:** one designated disposable Event; Admin create/update/poster/publish; anonymous Landing;
  direct detail; update propagation; USER authorization denial; sanitized evidence and cleanup plan.
- **Non-goals:** production deploy, load test, registration, recap, calendar, ordering/windows or
  destructive database reset.
- **Backend changes:** none; a discovered defect returns to its owning task.
- **Frontend changes:** none; a discovered defect returns to its owning task.
- **Database changes:** verify `alembic current`/expected head only; no manual SQL or migration here.
- **Storage changes:** verify configured private bucket and exercise upload/replacement only through
  Admin UI/API; no Dashboard-direct object manipulation.
- **Security requirements:** use separate ADMIN and normal USER/anonymous sessions; redact email,
  cookies, tokens, signed URLs, object keys and credentials from evidence.
- **Acceptance Criteria / DoD:** Scenario A Admin creates/opens Event, uploads/changes poster, sets
  name/description/date-time/location and saves successfully; Scenario B anonymous/user Landing shows
  it with correct poster; Scenario C click and direct refresh show correct detail; Scenario D Admin
  edit/poster replacement propagates after refetch/F5 and within 60 seconds; Scenario E USER Admin UI
  is denied and direct Admin API mutation returns 403. No unrelated Buddy regression is observed.
- **Tests/Gates:** record deployed SHAs, timestamp, environment, PASS/FAIL per A–E, browser console/
  network sanity, 401/403/CSRF evidence and cleanup outcome without sensitive payloads.
- **Staging acceptance:** this task is the acceptance. Only a complete signed PASS authorizes enabling
  the production Event launch flag; failure keeps the release guard off.
- **Next Task:** explicit product/release approval; no automatic production deployment.


## Cross-reference occurrences outside extracted headings

- Legacy line 8265: - **Launch-scope integrity:** existing non-V2 P0 features must pass their own acceptance gates before production navigation advertises them. The Event/Event Slider/Admin Event track is restored to planned launch scope by controlling Part 27 and must pass \`ACCEPT-EVENT-001\`; until then its existing production feature gate remains off and placeholder routes are not advertised as delivered features.
- Legacy line 8338:   \`ACCEPT-EVENT-001\` passes. After that acceptance, production enables the Event track; the flag is
- Legacy line 8534:   -> ACCEPT-EVENT-001
- Legacy line 8621:   sensitive content during \`ACCEPT-EVENT-001\`.
- Legacy line 8844: - **Staging acceptance:** none; successful automation makes \`ACCEPT-EVENT-001\` ready.
- Legacy line 8845: - **Next Task:** \`ACCEPT-EVENT-001\`.
- Legacy line 8956: 13. \`ACCEPT-EVENT-001\` — Real Admin and public staging acceptance
- Legacy line 8971:   \`ACCEPT-EVENT-001\` with implementation/deployment fixes. A failing acceptance returns to the owner
- Legacy line 8980:   + public/USER flow is exclusively \`ACCEPT-EVENT-001\`.
- Legacy line 9095:    \`ADMIN-009 → FE-031 → FE-014B → EVS-007 → ACCEPT-EVENT-001\`.
