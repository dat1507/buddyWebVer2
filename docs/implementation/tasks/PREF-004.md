# PREF-004

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** PREF-003, FE-026/027/029; Frontend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7073-7101

#### PREF-004 — Custom preference tag/input/display UI

- **Status:** **Done 2026-09-27.** The frontend now manages and displays predefined plus profile-owned custom Interests, Languages and Activities through the owner preference snapshot, including custom-language proficiency and optimistic-version updates.
- **Purpose:** Let users manage and view the three combined signal sets.
- **Scope / likely files:** onboarding/profile form components, own-profile view, clients/types/locales.
- **Dependencies / ownership:** PREF-003, FE-026/027/029; Frontend.
- **Security:** render labels as text; client limits mirror but never replace server validation.
- **Acceptance / DoD:** accessible add/remove/edit for predefined/custom values; duplicate normalized labels prevented/explained; reload round-trip preserves labels and proficiency.
- **Tests/gates:** component, keyboard/a11y, normalization-contract and API integration tests.
- **Non-goals:** public catalog creation or AI suggestions.

**Implementation:** Shared accessible tag controls normalize display input consistently with the
PREF-002 contract, enforce combined per-kind limits, explain same-kind normalized duplicates and
active predefined EN/DE collisions, and keep custom labels as inert text. Profile Edit and onboarding
atomically submit predefined and custom Interests, Languages and Activities through the owner-only
preference API with the current optimistic version; custom Language proficiency is included in the
same snapshot. Save readiness is scoped to the editable catalog instead of blocking Interest changes
on an unrelated pending Language catalog (and vice versa). Profile display and fresh query hydration
render the persisted server snapshot; no browser storage is used as a persistence fallback.

**Verification (2026-09-27):** PREF-004 targeted frontend tests: 40 passed; profile/onboarding
regression: 67 passed; full frontend: 545 passed / 54 files. Strict TypeScript, ESLint, Prettier and
production build pass. Browser acceptance passes predefined + custom Interest, Language/proficiency
and Activity save/F5 round-trips, proficiency changes, removals, active predefined collision
(`photography`/`Photography`), normalized custom duplicate rejection (`Formula 1` variants), observed
PUT persistence and sanitized client-visible errors.

**REC-004 handoff:** Completed below after its declared `REC-003` and `EMAIL-005` dependencies.


## Cross-reference occurrences outside extracted headings

- Legacy line 6859: | PREF-004 (**Done 2026-09-27**) | Preference tag UI | PREF-003, FE-026/027/029 | Add/edit/display predefined + custom values | Component/a11y/integration tests |
- Legacy line 7017: - **Status:** **Done 2026-09-27.** The backend now owns one bounded, deterministic preference identity contract with a display-safe label and an NFKC/whitespace/casefold key; PREF-003/PREF-004 remain unimplemented.
- Legacy line 8163: PREF-001 → PREF-002 → PREF-003 → PREF-004
- Legacy line 8216: - EMAIL-005 and PREF-004 can use contract fixtures after API schemas stabilize.
- Legacy line 8224: Final integration convergence: EMAIL-005 + PREF-004 + PROFILE-V2-002 + REC-004 + INV-007/008/009 + BUDDY-003 + CHAT-004/005 + ADMIN-V2-002 + SEM-007 + OPS-003 must all pass before ACCEPT-001.
