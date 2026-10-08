# AUTH-002

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** FE-005, FE-006

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 1963-1977

#### AUTH-002 — UI-only Student Registration Page

**Status**: Completed (✅)

- Provide an accessible Student Registration form at `/register`, with no role selector and no ability to register an Admin.
- The UI-only page must not fake account creation, JWT creation, or dashboard redirects before the backend contract is connected.

**Implementation Notes**:
- Replaced the `/register` placeholder route with `UserRegistrationPage` while retaining the existing public layout.
- Limited account fields to the plan's User account contract: email and password. Student profile data remains deferred to the Profile UI phase.
- Added the explicit consent checkbox required by the plan's GDPR section; no role field, Admin option, or `/adminLogin` link is exposed.
- Added responsive EN/DE UI, field-level validation, browser-appropriate autocomplete attributes, and focus movement to the first invalid field.
- A valid UI-only submit displays a neutral backend-pending status without calling an API, persisting account/token data, or navigating away from `/register`.
- Added route-level tests covering semantics, validation, consent, focus behavior, localization, UI-only submission, and the absence of Admin registration paths.


## Cross-reference occurrences outside extracted headings

- Legacy line 1280: | AUTH-002 | Create User Registration page (/register) | 3 | FE-005, FE-006 | P0 |
- Legacy line 1287: > **Approved UI-first exception**: AUTH-001, AUTH-002, and AUTH-003 are implemented as UI-only pages before Backend Foundation. They may include responsive layouts, accessible forms, client-side validation, and loading/error presentation contracts, but must not simulate successful authentication, create fake tokens, or perform fake role redirects. Backend connectivity remains exclusively in AUTH-021 through AUTH-023.
- Legacy line 1295: | FE-AUTH-ENTRY-001 | Add desktop Sign in menu with User Login and Create Student Account only | AUTH-001, AUTH-002 | P0 |
- Legacy line 1296: | FE-AUTH-ENTRY-002 | Add direct User Login and Create Student Account actions to the mobile drawer | AUTH-001, AUTH-002 | P0 |
- Legacy line 1297: | FE-AUTH-ENTRY-003 | Route Join the Community to \`/register\` | AUTH-002 | P1 |
- Legacy line 1832: - AUTH-001, AUTH-002, and AUTH-003 may be completed as UI-only pages before Backend Foundation. API authentication, JWT persistence, role redirects, and protected-route behavior remain deferred to AUTH-021 through AUTH-023.
- Legacy line 1833: - \`Join the Community\` will route to \`/register\` after AUTH-002 exists.
- Legacy line 2024: - \`Join the Community\` becomes an internal navigation action to \`/register\` only after AUTH-002 exists.
- Legacy line 4241: Done:    AUTH-002        Create Student Registration UI (/register) [completed 2026-09-10]
