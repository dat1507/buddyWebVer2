# AUTH-007

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** BE-006

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 2578-2642

### AUTH-007 — Define UserRole enum (USER, ADMIN) in models

**Status**: Completed (✅) on 2026-09-16
**Objective**: Establish one shared, string-compatible application role contract for the future User
model, API schemas and authorization dependencies without creating persistence or authentication
behavior ahead of AUTH-008 and later tasks.

The registry supplied the task title, priority and BE-006 dependency but no dedicated task contract.
The operational acceptance criteria below keep the implementation deliberately limited to the role
primitive required by the next authentication tasks.

**Operational Acceptance Criteria**:

- [x] `UserRole` is defined in the model layer with exactly `USER` and `ADMIN` members and exact
  uppercase string values.
- [x] The enum is string- and JSON-compatible for future SQLAlchemy, Pydantic and API reuse.
- [x] `UserRole` is exported from `app.models` as the canonical import path.
- [x] Unknown, lowercase, empty and expanded role values are rejected rather than normalized.
- [x] No User table, migration, password/session/token logic, route guard, permission grant or RLS
  policy is introduced ahead of its owning task.
- [x] Focused tests cover membership, values, serialization and invalid inputs; all backend quality
  gates remain green.

**Files Created**:

- `apps/api/app/models/user.py`
- `apps/api/tests/test_user_role.py`

**Files Modified**:

- `apps/api/app/models/__init__.py`
- `apps/api/README.md`
- `implementation_plan_vgu_buddy.md`

**Implementation Notes**:

- Used Python 3.12 `StrEnum`, so role members behave as strings while retaining an explicit enum
  type. The member names and stored/API values are both uppercase to match the approved auth flow.
- Kept the enum in `models/user.py`, the planned home of the AUTH-008 User model, and re-exported it
  through `app.models` to avoid competing definitions in services or schemas.
- Role labels are data, not authorization. Later endpoints must derive roles from verified server
  state; public registration must always assign `USER`, and admin APIs must still enforce the
  server-side `require_role(ADMIN)` dependency.

**Verification Results**:

- Focused `UserRole` tests — PASS; exact members/values, string and JSON serialization, and four
  invalid-value classes are covered.
- `python -m pytest` — PASS, 50 tests.
- `ruff check .` — PASS.
- `mypy app tests` — PASS, strict mode over 21 source files.
- Alembic `history` / `heads` — PASS; no migration was added and the existing baseline remains the
  single head.
- `python -m build --no-isolation` — PASS on a clean Python 3.12 dependency installation.
- `python -m pip_audit --strict -r requirements.lock` — PASS, no known vulnerabilities found.
- Frontend format, lint, type-check, 80 tests and production build — PASS.

**Database Changes**: None.
**Environment Variables Added**: None.
**Business API Changes**: None.
**Security Remediation TODO**: The exposed legacy Gemini API key remains pending revocation and must
be revoked before any future Gemini/chatbot integration. It was not used by AUTH-007 and does not
block unrelated authentication foundation work.
**Next Task**: `AUTH-008 — Create User database model with role field`.


## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1310: | AUTH-007 | Define UserRole enum (USER, ADMIN) in models — ✅ Completed | 1 | BE-006 | P0 |
- Legacy line 1311: | AUTH-008 | Create User database model with role field — ✅ Completed | 2 | AUTH-007 | P0 |
- Legacy line 2530: The original registry supplied the task title and its BE-001/AUTH-ARCH-001 dependencies only. The operational acceptance checks below make the minimal security boundary explicit without expanding into AUTH-007 or later authentication work.
- Legacy line 2576: **Next Task**: \`AUTH-007 — Define UserRole enum (USER, ADMIN) in models\`.
- Legacy line 2649: The registry supplied the task title, priority and AUTH-007 dependency but no dedicated task
- Legacy line 4261: Done: AUTH-007                Define UserRole enum (USER, ADMIN) in models [P0; Phase 5; completed 2026-09-16]
