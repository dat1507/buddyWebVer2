# AUTH-021

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 4857-4893

### AUTH-021 — Connect session client, registration, and auth bootstrap

**Task ID:** `AUTH-021`
**Change:** Updated existing; **Status:** Completed (2026-09-18); **Priority:** P0; **Phase:** 5
**Goal:** Connect existing auth forms and session state to real backend responses.
**Dependencies:** AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024
**Scope:** Credentialed client, CSRF, single-flight refresh, registration submission, /auth/me bootstrap, private-cache clearing.

**Acceptance Criteria:**

- [x] Registration creates USER and returns to /login; valid login restores actual role without local tokens. — Real browser + isolated PostgreSQL registration/login/reload PASS; live database checks confirm USER/unverified and actual USER/ADMIN roles. Integrated forms/client/store tests validate the real request/response contract, success-only navigation and absence of storage/cookie reads.
- [x] Session errors expose retry/pending states; logout or account switch clears profile/match/private-media queries; current public slider GETs continue working. — Pending/duplicate/error/retry tests (409/422/503/network), serialized old-family logout before account switch, targeted query cancellation/removal, late-response rejection, public GET/cache regressions and post-logout browser slider/EN-DE rendering PASS.

**Out of Scope:** Redesigning completed AUTH-001..003; profile routing is FE-038.

**Approved backend extension:** Reload loses readable memory-only CSRF while HttpOnly JWT/CSRF
cookies survive. `/me` returns User only, and pre-auth `/csrf` cannot authorize refresh/logout.
Added `GET /api/auth/csrf/session` using existing trusted-Origin/Referer utility, verified cookie
identity and owner-bound live family/current refresh JTI. Reuse valid same-session CSRF or issue
existing session-bound form; no-store/no-cache, no JWT response/rotation/session creation, no CORS
widening or persistence. Existing pre-auth and unsafe-method CSRF contracts remain unchanged.

**Verification (2026-09-18):** 25 recovery unit/security + 3 isolated PostgreSQL live tests PASS;
full backend **384 PASS / 10 existing opt-in Redis live SKIP**. Frontend **175 PASS**, including
transport, controller, real Zustand, integrated forms, cache and existing public UI checks.
Ruff lint/changed-file format, strict mypy (57 files), pip check/audit, frontend format/lint/strict
typecheck/build/npm audit PASS. Backend sdist/wheel build PASS. Real local browser registration →
login → reload recovery → logout PASS; runtime database inspection confirms USER and family
revocation; landing slider and German rendering work after logout, browser error console empty.
No new dependencies, runtime configuration, migrations or secrets committed.

**Limits retained:** Coordination is tab-local; copied access JWT residual 15-minute TTL + 30-second
skew remains AUTH-017's contract. AUTH-020 production Redis/TLS/ingress acceptance and legacy Gemini
revocation remain separate gates. Existing frontend chunk-size advisory and seven untouched backend
baseline formatter discrepancies do not fail required CI gates. AUTH-005/006 and role-specific
redirects/denial in AUTH-022/023 are not implemented here.


## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1287: > **Approved UI-first exception**: AUTH-001, AUTH-002, and AUTH-003 are implemented as UI-only pages before Backend Foundation. They may include responsive layouts, accessible forms, client-side validation, and loading/error presentation contracts, but must not simulate successful authentication, create fake tokens, or perform fake role redirects. Backend connectivity remains exclusively in AUTH-021 through AUTH-023.
- Legacy line 1325: | AUTH-021 | Connect session client, registration, and auth bootstrap — ✅ Completed | 2 | AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024 | P0 |
- Legacy line 1326: | AUTH-022 | Implement login flow: User login → role check → redirect — ✅ Completed | 2 | AUTH-021, AUTH-006 | P0 |
- Legacy line 1327: | AUTH-023 | Implement admin login flow: Admin login → role=ADMIN check → redirect — ✅ Completed | 2 | AUTH-021, AUTH-006 | P0 |
- Legacy line 1338: | FE-024 | Create User Settings page with real session actions | 2 | FE-021, AUTH-021, AUTH-025 | P1 |
- Legacy line 1832: - AUTH-001, AUTH-002, and AUTH-003 may be completed as UI-only pages before Backend Foundation. API authentication, JWT persistence, role redirects, and protected-route behavior remain deferred to AUTH-021 through AUTH-023.
- Legacy line 2166: the store, not server cookies/session or private query caches. AUTH-021 still owns \`/api/auth/me\`,
- Legacy line 2176: **Next development task**: \`AUTH-021 — Connect session client, registration, and auth bootstrap\`;
- Legacy line 3183: explicit for frontend integration in AUTH-021.
- Legacy line 3389:   intentionally not both accepted: clients must single-flight refresh, which remains AUTH-021.
- Legacy line 3431:   and matching cookie clearing; AUTH-021 owns frontend single-flight and private-cache handling.
- Legacy line 3599:   access recovery remains the frontend single-flight refresh flow in AUTH-021.
- Legacy line 3827: AUTH-004/AUTH-021 and is not implemented or claimed verified here. Backend dependency is satisfied,
- Legacy line 3862:   claimed. AUTH-021 must coordinate these frontend requests and invalidate private query caches.
- Legacy line 4278: Done: AUTH-021                Connect session client, registration, and auth bootstrap [P0; Phase 5; completed 2026-09-18]
- Legacy line 4397: The final acceptance is a gate, not a new implementation task: create one Admin through AUTH-019, register one Vietnamese and one international USER through AUTH-013/AUTH-021, complete both profiles through the existing Profile flow, run/preview/publish through the new Admin UI, accept from both user sessions, and verify the active Buddy result after reload. It must use PostgreSQL and the configured private storage service; no fake users, fake match result or frontend-only success state may satisfy it.
- Legacy line 4568: **Scope:** Zustand store and shared sanitized User types/validation, ready for AUTH-021 integration.
- Legacy line 4579: route guards, production deployment, Gemini. These remain AUTH-021/022/023/005/006 or existing gates.
- Legacy line 4582: source. No live browser/deployed auth claim. AUTH-024 frontend/cache AC remains pending AUTH-021.
- Legacy line 4588: **Dependencies:** AUTH-004, FE-006; current AUTH-021 bootstrap integration is reused.
- Legacy line 4598: - [x] AUTH-021 reload/refresh remains bounded without early private UI; existing auth/public/cache regressions and required gates pass. — StrictMode bootstrap, held final \`/me\` 200/401, rejected refresh, 503 feedback and pending logout/private-public cache tests PASS; real local browser cookies/database reload/logout acceptance PASS.
- Legacy line 4604: AUTH-021 installing refreshed identity before bootstrap's final \`/me\`; bootstrap now validates
- Legacy line 4626: **Dependencies:** AUTH-005; reuses AUTH-004 sanitized role and AUTH-021 verified bootstrap.
- Legacy line 4668: **Dependencies:** AUTH-021, AUTH-006 (complete on this branch).
- Legacy line 4683: retain manual retry. AUTH-021 form integration and User-page tests updated for resulting routing;
- Legacy line 4717: **Dependencies:** AUTH-021, AUTH-006 (complete on this branch).
- Legacy line 4740: detached. Landing renders only a whitelisted localized notice. AUTH-021 integration/Admin unit
- Legacy line 4845: - [x] A revoked refresh token cannot mint another session; frontend clears session and private query caches. — Existing backend replay/race acceptance retained; AUTH-021 PostgreSQL live replay/revocation PASS, real browser logout persists family revocation, frontend clears AUTH-004 and cancels/removes private queries while public slider cache survives. Late rotation/private-response and account-switch tests PASS.
- Legacy line 6537: **Dependencies:** FE-021, AUTH-021, AUTH-025
- Legacy line 6854: | EMAIL-005 (**Done 2026-09-24**) | Verification/change-email UX | EMAIL-002..004, AUTH-021 | Accurate Verified/Unverified UX and safe links | Component/integration/a11y tests |
- Legacy line 6971: - **Dependencies / ownership:** EMAIL-002..004, AUTH-021; Frontend.
