# PREF-003

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** PREF-001/002, BE-012/015; Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7040-7072

#### PREF-003 — Preference services and owner APIs

- **Status:** **Done 2026-09-27.** Owner-only APIs now persist and deterministically round-trip predefined and profile-owned custom Interests, Languages and Activities under one optimistic profile version.
- **Purpose:** Persist/read predefined and custom interests, languages and activities consistently.
- **Scope / likely files:** profile schemas/services/routes and readiness calculation using PREF-002 keys.
- **Dependencies / ownership:** PREF-001/002, BE-012/015; Backend.
- **Security:** owner-only mutations, CSRF, optimistic version, bounded arrays/labels and no unsafe reflection.
- **Acceptance / DoD:** custom languages retain proficiency; combined selections round-trip deterministically; completion counts valid predefined + custom selections; same-kind normalized duplicates are rejected by contract.
- **Tests/gates:** API/version/race/authorization/readiness and invalid-input tests.
- **Non-goals:** Admin taxonomy UI or global catalog writes.

**Implementation:** Authenticated USER owners can read and atomically replace the complete preference
snapshot, while the existing group-specific Interest and Language replacements now also support
custom values and a dedicated Activity catalog/replacement API completes the third namespace. All
mutations lock the owner profile, compare the submitted optimistic version, validate every group
before writes and increment the profile version once only when the canonical snapshot changes.
Custom labels use the PREF-002 identity service and are rejected with a stable sanitized 422 when
their same-kind key collides with an active predefined EN/DE label or another submitted custom
value; custom values never write into shared catalogs. Custom language proficiency is persisted,
internal normalized keys are never returned, and every response is ordered by stable identifiers,
codes or normalized identity. Legacy profile Activity input is backed by `ProfileActivity` while
retaining its response shape. Completion continues to require Interest and Language only, counts
valid predefined plus custom signals without double-counting normalized duplicates, and does not
gate existing users on Activity.

**Verification (2026-09-27):** PREF-003 targeted schema/service/API/profile/completion regression:
96 passed. Full backend: 854 passed / 20 configured live skips; Ruff, strict mypy (158 files),
dependency consistency, Alembic history/single head, sdist/wheel build, strict runtime dependency
audit and Compose validation pass. Unchanged frontend compatibility regression: format, ESLint,
strict TypeScript, production build, production dependency audit and 524 tests / 51 files pass; the
existing >500 kB chunk advisory and two existing React test warnings remain non-blocking. No
migration or dependency change was required; database head remains `0011_preference_persistence`.


## Cross-reference occurrences outside extracted headings

- Legacy line 6858: | PREF-003 (**Done 2026-09-27**) | Preference services/APIs | PREF-001/002, BE-012/015 | Owner CRUD, proficiency, bounded inputs | API/version/concurrency tests |
- Legacy line 6859: | PREF-004 (**Done 2026-09-27**) | Preference tag UI | PREF-003, FE-026/027/029 | Add/edit/display predefined + custom values | Component/a11y/integration tests |
- Legacy line 6860: | REC-001 (**Done 2026-09-27**) | V2 eligibility + safe DTO | AUTH-V2-001, PREF-003 | Opposite type, complete/opted-in/verified; no reservation | Policy/privacy tests |
- Legacy line 7017: - **Status:** **Done 2026-09-27.** The backend now owns one bounded, deterministic preference identity contract with a display-safe label and an NFKC/whitespace/casefold key; PREF-003/PREF-004 remain unimplemented.
- Legacy line 7078: - **Dependencies / ownership:** PREF-003, FE-026/027/029; Frontend.
- Legacy line 7115: - **Dependencies / ownership:** AUTH-V2-001, PREF-003; Backend.
- Legacy line 8163: PREF-001 → PREF-002 → PREF-003 → PREF-004
- Legacy line 8165: (AUTH-V2-001 + PREF-003) → REC-001 → REC-002 → REC-003
