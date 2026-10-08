# ADMIN-005

**Control-plane status:** DONE / PRESERVED
**Track:** admin
**Priority:** P0
**Dependencies (latest extracted):** FE-004 — DONE; shadcn configuration, shared Button primitive and modal-isolation convention verified.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 5175-5209

### ADMIN-005 — Create reusable ConfirmDialog component

- **Task ID:** `ADMIN-005`
- **Status:** Completed — 2026-09-19; **Priority:** P0; **Phase:** 7; **Cx:** 1
- **Dependencies:** FE-004 — DONE; shadcn configuration, shared Button primitive and modal-isolation convention verified.
- **Goal/scope:** Reusable caller-controlled confirmation UI. The registry supplied no extended task contract, so the acceptance record below is derived from its scope, existing modal/accessibility conventions and the needs of declared dependents. Domain mutations and deletion policies remain in later tasks.

**Definition of Done / acceptance derived from the registry scope and existing design conventions:**

- [x] Controlled open state and confirmation callback, caller-owned localized title/description/action labels, default or destructive action styling, and optional dependency-disabled confirmation.
- [x] Caller-driven pending and error states; pending prevents duplicate confirmation and cancellation through button, Escape or backdrop without inventing mutation behavior or automatic close.
- [x] Portalled `alertdialog` with instance-unique accessible name/description/error relationships, modal background isolation, body scroll lock, safe initial focus, keyboard focus containment and focus/state restoration.
- [x] Reuses shared Button/theme and modal-isolation infrastructure. No dependency, locale key, API, route, auth/session, persistence, environment or secret change.
- [x] Dedicated interaction/accessibility tests plus required frontend regressions, build/audit, browser behavior and repository CI/security review pass.

**Implementation:** `confirm-dialog.tsx` owns only modal presentation and interaction. The caller owns
business copy, async state, errors, dependency checks, mutation execution and the decision to close.
This keeps ADMIN-010 and ADMIN-SLIDER-003 domain policy outside the primitive while allowing them to
reuse its destructive, disabled, pending and error states.

**Verification (2026-09-19):** 8 dedicated ADMIN-005 tests PASS; full frontend 446 PASS / 38 files.
Format, lint, typecheck, production build and production npm audit (zero vulnerabilities) PASS.
Isolated browser acceptance PASS for portal isolation, safe initial focus, keyboard loop, Escape/
focus restoration, dependency-disabled confirmation and pending duplicate/dismissal protection; a
real-browser pending focus-loss edge was found and fixed. Backend CI regression remains 381 PASS /
13 configured live skips; pip check, Ruff, strict mypy (57 files), Alembic graph, package build,
strict lockfile pip-audit and Compose validation PASS. No live database/API gate applies to this pure
frontend primitive.

**Next development task:** EVT-008 — Create audit log model, migration and service, P0 / Phase 10 /
Cx2; dependency AUTH-009 DONE, READY. It is not implemented here.

**Out of Scope:** Event/slider list, mutation, deletion dependency resolution, API/cache/database,
audit implementation, AUTH-020 production operator gate and deployment.


## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1348: | ADMIN-005 | Create reusable ConfirmDialog component — ✅ Completed | 1 | FE-004 | P0 |
- Legacy line 1416: | ADMIN-010 | Create event deletion with dependency-aware confirmation | 2 | ADMIN-005, ADMIN-006, EVT-009 | P0 |
- Legacy line 1429: | ADMIN-SLIDER-003 | Add publish/draft/archive, active toggle, and delete confirmation controls | 3 | ADMIN-005, ADMIN-SLIDER-001 | P0 |
- Legacy line 4289: Done: ADMIN-005               Create reusable ConfirmDialog component [P0; Phase 7; completed 2026-09-19]
- Legacy line 5169: **Next development task:** ADMIN-005 — Create reusable ConfirmDialog component, P0 / Phase7 / Cx1;
- Legacy line 6202: **Dependencies:** ADMIN-005, ADMIN-006, EVT-009
- Legacy line 6891: | SEM-007 | Semester Management UI | SEM-005/006, ADMIN-005 | Counts/warnings/phrase/re-auth/status/restore UX | UI/a11y/e2e tests |
- Legacy line 8078: - **Dependencies / ownership:** SEM-005/006, ADMIN-005; Frontend.
- Legacy line 8152: This graph shows V2 tasks; already-existing prerequisite IDs such as AUTH-008/009, BE-012, FE-029, EVS-003 and ADMIN-005 remain mandatory exactly as listed in each task contract.
- Legacy line 8191: (SEM-005 + SEM-006 + ADMIN-005) → SEM-007
