# FE-CLOSEOUT-001

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P0
**Dependencies (latest extracted):** FE-VERIFY-001

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2049-2061

#### FE-CLOSEOUT-001 — Restore Formatting and Type-check Gates

**Status**: Completed (✅)

- Restore Prettier compliance for the Testimonials Marquee implementation and its component tests without changing runtime behavior.
- Add a dedicated `typecheck` package script so the strict TypeScript gate can run independently from the production build.

**Implementation Notes**:
- Applied Prettier-only formatting changes to `apps/web/src/components/landing/testimonials-marquee.tsx` and `apps/web/src/components/landing/testimonials-marquee.test.tsx`; no marquee logic or test assertions changed.
- Added `"typecheck": "tsc -b"` to `apps/web/package.json`.
- Confirmed the full Frontend quality suite: Prettier check, ESLint, strict type-check, all 76 tests, and production build pass.
- Existing scroll-to-top test-environment warnings and the remaining accessibility closeout findings stay outside this task and remain pending.


## Cross-reference occurrences outside extracted headings

- Legacy line 1300: | FE-CLOSEOUT-001 | Restore formatting and type-check quality gates | FE-VERIFY-001 | P0 |
- Legacy line 1301: | FE-CLOSEOUT-002 | Isolate modal background content from assistive technology | FE-CLOSEOUT-001 | P0 |
- Legacy line 4248: Done:    FE-CLOSEOUT-001    Restore formatting and type-check gates [completed 2026-09-11]
