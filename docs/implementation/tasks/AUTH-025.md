# AUTH-025

**Control-plane status:** PLANNED / BACKLOG
**Track:** auth-email
**Priority:** P1
**Dependencies (latest extracted):** AUTH-024, AUTH-010

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6517-6531

### AUTH-025 — Implement authenticated password change endpoint

**Task ID:** `AUTH-025`
**Change:** New; **Status:** Planned; **Priority:** P1; **Phase:** 5
**Goal:** Supply the backend dependency already implied by Settings.
**Dependencies:** AUTH-024, AUTH-010
**Scope:** POST /api/auth/change-password with current-password verification and session revocation.

**Acceptance Criteria:**

- [ ] Wrong current password and invalid CSRF fail; password changes invalidate refresh sessions and require login again.
- [ ] Response/logs contain no password, hash or session token.

**Out of Scope:** Forgot-password email delivery or passwordless login.


## Cross-reference occurrences outside extracted headings

- Legacy line 1329: | AUTH-025 | Implement authenticated password change endpoint | 2 | AUTH-024, AUTH-010 | P1 |
- Legacy line 1338: | FE-024 | Create User Settings page with real session actions | 2 | FE-021, AUTH-021, AUTH-025 | P1 |
- Legacy line 4357: Next: AUTH-025                Implement authenticated password change endpoint [P1; Phase 5]
- Legacy line 4389: - **P2 — POST-DEMO for this deadline:** the remaining Event/EventSlider/Admin Event lane, AUTH-025/FE-024, event registration/calendar, feedback/history and MATCH-005/006 research. Their existing product-release priorities and dependencies are unchanged; this label is only the September 22 demo schedule.
- Legacy line 6537: **Dependencies:** FE-021, AUTH-021, AUTH-025
