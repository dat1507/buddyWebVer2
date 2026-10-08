# PREF-001

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** BE-009/010; Database + Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6988-7014

#### PREF-001 — Activity and custom-preference persistence

- **Status:** **Done 2026-09-27.** Revision `0011_preference_persistence` adds the independent Activity catalog, profile/activity relation and profile-owned custom preference persistence with least-privilege backend access.
- **Purpose:** Represent all confirmed matching signals without polluting shared catalogs.
- **Scope / likely files:** Activity/ProfileActivity/ProfileCustomPreference models, exports, seed strategy and migration from current preferred-activity IDs.
- **Dependencies / ownership:** BE-009/010; Database + Backend.
- **Security:** bounded lengths/counts, kind/proficiency checks, backend-only schema/grants, cascade with profile.
- **Acceptance / DoD:** predefined activities are independent from Interests; custom values are profile-owned and unique by normalized key/kind; catalogs survive semester reset, custom rows do not.
- **Tests/gates:** migration, constraint, cascade, seed idempotency and permission tests.
- **Non-goals:** globalizing custom values or synonym/AI matching.

**Implementation:** `Activity` is a separate localized shared catalog and `ProfileActivity` uses a
unique profile/catalog pair with profile cascade and catalog restrict semantics.
`ProfileCustomPreference` stores only profile-owned `INTEREST`, `LANGUAGE` or `ACTIVITY` values,
bounded display/normalized fields, scoped language proficiency and unique
`(profile_id, kind, normalized_key)` identity. The migration snapshots every legacy Interest row
that could have supplied `preferences.preferred_activity_ids` into the independent Activity catalog
while preserving stable IDs/labels and materializes profile selections; malformed or orphaned legacy
values fail the migration instead of being discarded. Catalog seed/import is idempotent, and the new
tables revoke browser/Data API access before granting only the required runtime operations.

**Verification (2026-09-27):** Model/offline migration tests and the guarded disposable PostgreSQL
upgrade/constraint/cascade/permission/downgrade/re-upgrade acceptance pass. Full backend: 805 passed /
20 configured live skips; Ruff, strict mypy (154 files), dependency consistency/audit, Alembic
history/head/check, package build and Compose validation pass. No dependency, API or frontend change
was added.


## Cross-reference occurrences outside extracted headings

- Legacy line 6856: | PREF-001 (**Done 2026-09-27**) | Custom/activity persistence | BE-009/010 | Profile-owned normalized custom values; Activity catalog | Migration/constraint tests |
- Legacy line 6857: | PREF-002 | Normalized preference identity service | PREF-001 | NFKC/casefold rules and deterministic keys | Unicode/property tests |
- Legacy line 6858: | PREF-003 (**Done 2026-09-27**) | Preference services/APIs | PREF-001/002, BE-012/015 | Owner CRUD, proficiency, bounded inputs | API/version/concurrency tests |
- Legacy line 7020: - **Dependencies / ownership:** PREF-001; Backend.
- Legacy line 7029: and Unicode casefold in that order. The service reuses the PREF-001 120/255-character storage
- Legacy line 7035: pathological-input and PREF-001 identity-compatibility tests pass. Full backend: 836 passed / 20
- Legacy line 7045: - **Dependencies / ownership:** PREF-001/002, BE-012/015; Backend.
- Legacy line 8163: PREF-001 → PREF-002 → PREF-003 → PREF-004
- Legacy line 8205: 2. \`EMAIL-002..005\`, \`OPS-001..003\`, \`PREF-001..004\` and \`REC-001..003\` are complete. Proceed with
- Legacy line 8215: - PREF-001/002/003 can run alongside EMAIL-001/001A/MAIL-001/EMAIL-002.
