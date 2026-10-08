# AUTH-ARCH-001

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** FE-HYGIENE-002

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 979-990

### Approved Authentication Transport Contract (`AUTH-ARCH-001`)

- **Transport**: JWT access and refresh tokens are stored only in backend-set HttpOnly cookies. The API never returns tokens in JSON, and frontend JavaScript never reads, persists, or sends bearer tokens.
- **Cookie policy**: Production uses `Secure`, `HttpOnly`, `SameSite=Lax`, and `Path=/`; omit `Domain` and use a `__Host-` cookie prefix when the final deployment host supports it. Local HTTP development may use explicitly named non-`__Host-`, non-`Secure` development cookies only.
- **Frontend state**: Zustand holds only `status: unknown | loading | authenticated | unauthenticated`, a sanitized `user`, and `role`. It has no `token` or `refreshToken` field and is not persisted to Web Storage. `/api/auth/me` restores the session after reload.
- **Route guards**: `ProtectedRoute` and `RoleGuard` show a neutral pending state while session status is `unknown` or `loading`; they redirect only after `/api/auth/me` resolves, preventing reload-time redirect flicker.
- **API client**: All API calls use a single client configured with `credentials: "include"`. A 401 may trigger one single-flight refresh attempt and one request retry; refresh failure clears in-memory session state and redirects through the normal unauthenticated flow.
- **CSRF**: `GET /api/auth/csrf` establishes a pre-auth CSRF context and returns a signed double-submit value; successful login rotates it and binds the replacement to the refresh session. The readable CSRF value is held in memory and sent as `X-CSRF-Token` on every state-changing request, including register, login, refresh, logout, uploads, and Admin mutations. The backend also validates `Origin`/`Referer`; safe methods never change state.
- **CORS/deployment**: Production must expose the API on the same site as the frontend, preferably through a Vercel `/api` reverse proxy to a WebSocket-capable first-party API host. Credentialed CORS uses an explicit origin allowlist and explicit methods/headers—never `*`. Frontend environment configuration points to the same-site API boundary.
- **RBAC boundary**: Frontend `RoleGuard` is UX only. Every protected backend route derives identity and role solely from the verified access-cookie JWT and enforces `require_auth`/`require_role`; no role value supplied by the client is trusted.
- **Cache/logout**: Auth responses use `Cache-Control: no-store`. Logout revokes/invalidates the refresh session, clears both auth cookies and the CSRF cookie, and clears the frontend session state.


### Legacy lines 2108-2135

#### AUTH-ARCH-001 — Finalize JWT Transport and Frontend Session Boundary

**Status**: Completed (✅)

- Choose exactly one browser authentication transport before Backend Foundation and remove the conflict between the existing HttpOnly-cookie security table and the token-bearing Zustand task.
- Define cookie, CSRF, credentialed-request, refresh, logout, RBAC, CORS/deployment, and frontend bootstrap contracts precisely enough for backend and frontend auth tasks to share one implementation target.
- Do not add runtime authentication code during this architecture-only gate.

**Decision**: Use HttpOnly access/refresh JWT cookies. Do not use a frontend-managed bearer token and do not persist auth tokens in Zustand, localStorage, sessionStorage, or IndexedDB.

**Implementation Notes**:
- Updated architecture diagrams, security controls, API permissions, test cases, task descriptions, dependencies, and the Part 22 assessment to use one cookie-based session contract.
- Defined Zustand as a non-persisted view of sanitized session state, restored from `/api/auth/me`; the backend remains the sole authorization authority.
- Added the signed, session-bound double-submit CSRF contract and explicit Origin/Referer validation because SameSite alone is defense in depth, not the complete CSRF control.
- Required a same-site production API boundary, preferably a Vercel `/api` reverse proxy to a WebSocket-capable API host, plus exact credentialed CORS configuration for any cross-origin development or deployment topology.
- Added `AUTH-011A` so CSRF service and endpoint work is independently testable before register/login/refresh mutations are implemented.
- Decision basis: OWASP advises against storing session identifiers in Web Storage and recommends HttpOnly cookies; OWASP also recommends CSRF tokens in addition to SameSite for general deployments. MDN documents cookie credential behavior and secure cookie attributes, while FastAPI requires explicit origins/methods/headers when credentialed CORS is enabled.
- No runtime source or dependency was changed in this architecture-only task. Prettier, ESLint, strict type-check, all 80 Frontend tests, and production build pass; the existing Vite chunk-size advisory remains non-blocking.
- The Frontend completion and authentication architecture gates are satisfied. Backend Foundation may begin with `BE-001`; the literal production hostname/proxy target remains environment-specific deployment configuration, while the required first-party/same-site topology is fixed by this contract.

**Authoritative References**:
- [OWASP HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [MDN Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie)
- [MDN Fetch credentials](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch#including_credentials)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)


## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1242: | BE-007 | Configure credentialed CORS with explicit frontend origins, methods, and headers — ✅ Completed | 1 | BE-001, AUTH-ARCH-001 | P0 |
- Legacy line 1282: | AUTH-004 | Create non-persisted Zustand session store (status, user, role; no tokens) — ✅ COMPLETED | 2 | FE-001, AUTH-ARCH-001 | P0 |
- Legacy line 1304: | AUTH-ARCH-001 | Decide JWT transport and frontend auth-state boundary before Auth Backend | FE-HYGIENE-002 | P0 |
- Legacy line 1314: | AUTH-011 | Create JWT cookie service (create/verify access + rotating refresh tokens) — ✅ Completed | 3 | BE-001, AUTH-ARCH-001 | P0 |
- Legacy line 1315: | AUTH-011A | Create signed CSRF service and \`GET /api/auth/csrf\` endpoint — ✅ Completed | 2 | BE-001, AUTH-ARCH-001 | P0 |
- Legacy line 2139: AUTH-ARCH-001; detailed operational acceptance is recorded in PART 25. No auth UI wiring performed.
- Legacy line 2530: The original registry supplied the task title and its BE-001/AUTH-ARCH-001 dependencies only. The operational acceptance checks below make the minimal security boundary explicit without expanding into AUTH-007 or later authentication work.
- Legacy line 2559: - Allowed \`X-CSRF-Token\` now so the approved double-submit CSRF transport can be implemented later without widening CORS to arbitrary headers. \`Authorization\` remains disallowed because AUTH-ARCH-001 prohibits frontend-managed bearer tokens.
- Legacy line 2900: The registry and AUTH-ARCH-001 fixed the browser transport and lifetimes but did not specify a JWT
- Legacy line 3276: The registry supplied the task title, dependencies and AUTH-ARCH-001 transport contract. The
- Legacy line 3367: The registry supplied the task title, dependencies and AUTH-ARCH-001 cookie transport contract. The
- Legacy line 4252: Done:    AUTH-ARCH-001      Decide JWT transport and frontend auth-state boundary [completed 2026-09-11]
- Legacy line 4560: **Out of Scope:** Returning whole profile or modifying AUTH-ARCH-001.
- Legacy line 4566: **Dependencies:** FE-001, AUTH-ARCH-001 (both completed).
- Legacy line 4570: **Operational Acceptance Criteria** (derived from the registry and AUTH-ARCH-001 before coding):
- Legacy line 4593: from that registry and the approved AUTH-ARCH-001 guard contract, rather than a new role policy:
- Legacy line 4630: requirement, AUTH-ARCH-001 pending contract and PART 22 authorization layering:
- Legacy line 4672: requirement, AUTH-ARCH-001, the approved sanitized login response and PART 22 role-routing diagram:
- Legacy line 4720: The registry supplies title/dependencies only. Operational checks derive from AUTH-ARCH-001,
