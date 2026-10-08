# ADMIN-SLIDER-001

**Control-plane status:** SUPERSEDED / DO NOT IMPLEMENT
**Track:** events
**Priority:** P0
**Dependencies (latest extracted):** ADMIN-004, EVS-006

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved references

No standalone legacy heading exists. Registry/order references are retained below; create a complete
contract before execution when the control-plane status requires recontracting.

## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1427: | ADMIN-SLIDER-001 | Create \`/admin/event-sliders\` list with status/visibility filters and loading/error/empty states | 3 | ADMIN-004, EVS-006 | P0 |
- Legacy line 1428: | ADMIN-SLIDER-002 | Create EN/DE EventSlider create/edit form with Event link, CTA, schedule, and image upload | 4 | ADMIN-SLIDER-001, EVS-003 | P0 |
- Legacy line 1429: | ADMIN-SLIDER-003 | Add publish/draft/archive, active toggle, and delete confirmation controls | 3 | ADMIN-005, ADMIN-SLIDER-001 | P0 |
- Legacy line 1430: | ADMIN-SLIDER-004 | Add transactional drag/drop ordering with optimistic UI and rollback | 3 | ADMIN-SLIDER-001, EVS-006 | P0 |
- Legacy line 4351: Next: ADMIN-SLIDER-001        Create \`/admin/event-sliders\` list with status/visibility filters and loading/error/empty states [P0; Phase 11A]
- Legacy line 4379: Event/Admin: **EVT-001/002/010 → EVT-003 → EVT-004/005/006 → EVT-009/011 → EVT-012/013 → ADMIN-006..010 + ADMIN-EVT-001 → EVS-001/002/004/005/006/007 → ADMIN-SLIDER-001..004 → FE-031 → FE-014B**. Existing EVS-003 has already supplied shared storage. The two tracks may proceed independently after shared auth/storage/audit; for the demo deadline, pause the Event lane after completed EVT-004 and resume it after the Matching demo slice. This is sequencing guidance, not an instruction to spawn agents.
- Legacy line 5167: matching, security or deployment credit. ADMIN-006/012/ADMIN-SLIDER-001 still need backend contracts.
- Legacy line 8514: - \`ADMIN-SLIDER-001..004\`: separate slider list/form/status/drag-order UI; replaced by
