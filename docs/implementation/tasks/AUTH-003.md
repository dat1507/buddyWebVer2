# AUTH-003

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** FE-005, FE-006

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 1978-1992

#### AUTH-003 — UI-only Admin Login Page

**Status**: Completed (✅)

- Provide a visually distinct Admin Login form at `/adminLogin`, reachable by direct URL only.
- The UI-only page must not fake authentication success, JWT creation, or dashboard redirects before the backend contract is connected.

**Implementation Notes**:
- Replaced the `/adminLogin` placeholder with `AdminLoginPage`, using a distinct restricted-area visual treatment and explicit administration context.
- Added accessible email/password controls, localized field validation, browser-appropriate autocomplete attributes, and focus movement to the first invalid field.
- Kept the route direct-URL-only: no `/adminLogin` link exists in the Navbar, mobile drawer, Footer, User Login page, or Student Registration page.
- Exposed no registration or role-selection controls and states that Admin accounts are provisioned during deployment, consistent with the plan's no-self-registration policy.
- A valid UI-only submit displays a neutral backend-pending status without calling an API, persisting tokens, checking a fake role, or navigating to an Admin route.
- Added EN/DE resources and route-level tests for the distinct Admin surface, validation, focus, localization, UI-only behavior, and public-discovery boundary.


## Cross-reference occurrences outside extracted headings

- Legacy line 1281: | AUTH-003 | Create Admin Login page (/adminLogin) — distinct visual | 2 | FE-005, FE-006 | P0 |
- Legacy line 1287: > **Approved UI-first exception**: AUTH-001, AUTH-002, and AUTH-003 are implemented as UI-only pages before Backend Foundation. They may include responsive layouts, accessible forms, client-side validation, and loading/error presentation contracts, but must not simulate successful authentication, create fake tokens, or perform fake role redirects. Backend connectivity remains exclusively in AUTH-021 through AUTH-023.
- Legacy line 1289: > AUTH-003 remains reachable only through the direct \`/adminLogin\` URL and must not be advertised in public navigation. Admin self-registration is prohibited.
- Legacy line 1832: - AUTH-001, AUTH-002, and AUTH-003 may be completed as UI-only pages before Backend Foundation. API authentication, JWT persistence, role redirects, and protected-route behavior remain deferred to AUTH-021 through AUTH-023.
- Legacy line 4242: Done:    AUTH-003        Create direct-URL-only Admin Login UI (/adminLogin) [completed 2026-09-11]
