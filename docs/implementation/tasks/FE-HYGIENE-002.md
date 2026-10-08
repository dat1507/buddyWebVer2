# FE-HYGIENE-002

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P0
**Dependencies (latest extracted):** FE-CLOSEOUT-003

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2092-2107

#### FE-HYGIENE-002 — Verify Auth Layout Changes and Restore Repository Hygiene

**Status**: Completed (✅)

- Review the pending User Login, Student Registration, and Admin Login layout changes before accepting them into the baseline.
- Keep only changes that improve centering, responsive sizing, and overflow containment without altering the UI-only authentication behavior or public Admin discovery policy.
- Remove the two empty, untracked `package-lock.json` files generated outside the actual Frontend package while retaining the canonical tracked `apps/web/package-lock.json`.
- Finish with a clean, recoverable Git working tree and a dedicated scoped commit.

**Implementation Notes**:
- Added horizontal centering to the shared flex layout pattern used by `/login`, `/register`, and `/adminLogin`.
- Balanced the Admin Login desktop grid, increased its bounded maximum width, added shrink-safe `min-w-0` containment to both columns, and made the administration heading scale across breakpoints.
- Browser verification in German at 375, 768, 1280, and 1440 px confirmed centered auth surfaces, the intended one-column/two-column Admin layout, no document-level horizontal overflow, no clipped form content, and no console warnings or errors.
- Removed the empty untracked lockfiles at the repository root and `apps/`; `apps/web/package-lock.json` remains the single canonical npm lockfile.
- Prettier, ESLint, strict type-check, all 80 tests, and production build pass. The existing Vite chunk-size advisory remains deferred.


## Cross-reference occurrences outside extracted headings

- Legacy line 1303: | FE-HYGIENE-002 | Verify pending auth layout changes and restore a clean working tree | FE-CLOSEOUT-003 | P0 |
- Legacy line 1304: | AUTH-ARCH-001 | Decide JWT transport and frontend auth-state boundary before Auth Backend | FE-HYGIENE-002 | P0 |
- Legacy line 4251: Done:    FE-HYGIENE-002     Verify auth layouts and restore repository hygiene [completed 2026-09-11]
