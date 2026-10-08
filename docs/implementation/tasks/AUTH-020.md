# AUTH-020

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** P0
**Dependencies (latest extracted):** BE-001; current AUTH-013/014/015/016 identity and transaction contracts.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 3801-3822

### AUTH-020 — Rate limiting middleware (SlowAPI)

**Status**: Implemented; local/live acceptance PASS; production acceptance pending operator
configuration (2026-09-17). See PART 25 for the approved detailed contract and acceptance checklist.

- User-approved quotas: USER 120/minute, ADMIN 60/minute, fixed 60-second windows.
- Explicit ASGI IP gate and persisted-user quota checks cover the five current auth endpoints;
  safe generic 429/Retry-After, credentialed CORS and uniform 5-failure/15-minute account lockout.
- Shared TLS Redis is required in production; memory is explicitly local/test only. Missing/unsafe
  configuration and storage failure produce sanitized 503 with no fallback. No migration/compose
  change, new public recovery endpoint, production secret generation or external provisioning.
- Regression security hardening: reject noncanonical base64 CSRF encodings. Original tampering
  test remains enabled; deterministic pad-bit regression added. Generated valid tokens are unchanged.
- Full backend 324 tests PASS on Python 3.14 and CI-compatible Python 3.12 (43 AUTH-020 checks plus canonical-CSRF regression); Redis/process/
  concurrency and real least-privilege PostgreSQL auth/database-health acceptance PASS. Backend
  lint/format/strict typecheck/build/dependency audit and frontend 80 tests/quality gates PASS.
- Production Redis URI, real TLS/network access, trusted-proxy allowlist and deployed smoke remain
  **not verified**. Configure secrets on the server, not in source or chat, before release acceptance.
- Legacy Gemini: **⚠️ Still pending — revoke before any future Gemini/chatbot integration.**

**Next development task**: `AUTH-024 — Implement session logout endpoint`; not executed by AUTH-020.


### Legacy lines 4762-4833

### AUTH-020 — Rate limiting middleware (SlowAPI)

**Task ID:** `AUTH-020`

**Change:** Detailed contract approved during execution; **Status:** Implemented; local/live acceptance PASS; production operator gate pending; **Priority:** P0; **Phase:** 5
**Dependencies:** BE-001; current AUTH-013/014/015/016 identity and transaction contracts.

**Approved Contract:**

- The user explicitly reversed the historical quotas: **USER = 120 requests/minute; ADMIN = 60
  requests/minute**. Fixed 60-second windows start on the first counted request; request N passes,
  N+1 is rejected. Fixed-window boundary bursts are a documented limitation, not a rolling guarantee.
- Scope: the five implemented auth endpoints (`csrf`, `me`, `register`, `login`, `refresh`), including
  trailing-slash/mount-prefix forms. Health/docs/unknown routes/OPTIONS are not limited by this task.
  Password reset is not implemented. Later protected routes must explicitly join the scope.
- All scoped traffic shares a 120/minute canonical transport-IP gate before validation/CSRF/database.
  Login after credential verification, `me`, and refresh after current-user reload additionally share
  the role quota by persisted user UUID. Never use caller-provided role, stale JWT role, session UUID,
  new login cookie or IP rotation to grant a fresh user quota. No extra identity query on public routes.
- Only use `request.client.host`; the limiter does not parse arbitrary forwarded headers. Uvicorn's
  trusted-proxy peer allowlist and real ingress path require deployment verification; no wildcard
  trust or guessed provider IP ranges. Normalize IPv6 aliases and IPv4-mapped IPv6. Distinct real IPs
  can distribute anonymous traffic, and shared NAT clients share the IP gate.
- Five credential failures in a fixed 15-minute failure window trigger a separate 15-minute lockout
  from the fifth failure. First five responses remain generic 401; subsequent attempts return generic
  429 before opening the database. Successful login resets failures but never clears an active lock.
  Apply the same policy to USER/ADMIN/unknown login identifiers to avoid role/account disclosure;
  invalid CSRF/shape/config/database errors do not count as wrong credentials. Existing admitted
  concurrent attempts can finish; targeted account denial of service is a known lockout tradeoff.
- Generic `429 {"detail":"Too many requests. Please try again later."}` plus positive integer
  `Retry-After`, no-store/no-cache; expose Retry-After via credentialed CORS. No new schema/migration.
- SlowAPI's public `limiter`/limits backend with an explicit pure-ASGI adapter avoids included-router
  discovery bypasses on current FastAPI. Redis I/O uses the thread pool with bounded socket timeouts.
- Shared Redis is required for production; memory is explicitly local/test only. Missing/invalid
  configuration or storage outage returns sanitized 503 without silent memory fallback. Production
  defaults to `APP_ENV=production` and requires a server-only TLS `rediss://` URL; Vercel environment
  markers prohibit memory. All instances must share URI/prefix; separate environments use separate
  storage/prefixes. Redis needs Lua support, retained TTL counters, sufficient capacity/no eviction.
- Keep the existing Vercel frontend + separate FastAPI backend architecture. Final Redis credentials,
  network/TLS, audited proxy allowlist and deployed smoke acceptance are operator-provided release
  gates. No production secret is generated/guessed or external infrastructure provisioned here.

**Acceptance Criteria:**

- [x] Exact USER 120 / ADMIN 60 quotas derive from current database role, not JWT/input.
- [x] All current auth routers are actually guarded; unrelated routes/OPTIONS remain unaffected.
- [x] Generic 429, Retry-After, safe cache/CORS headers; reset and identifier isolation pass.
- [x] Five wrong/unknown/Admin logins cause uniform 15-minute lockout, with no IP/instance bypass.
- [x] Valid login/register/me/refresh and cookie/CSRF/transaction regression remain correct.
- [x] Shared live Redis counters survive worker reconstruction and concurrent admission is atomic.
- [x] Missing/unsafe config and storage outages fail closed, without credential disclosure/fallback.
- [x] Full backend/frontend quality gates and dependency/secret review pass.
- [ ] Operator configures production Redis/TLS/ingress and deployed multi-instance/proxy smoke passes.

**Out of Scope:** Production provisioning/secrets, logout, recovery/unlock, Gemini/chatbot integration.

**Verification evidence (2026-09-17):** Full backend 324 tests PASS on Python 3.14 and 3.12, including 43 AUTH-020
memory/live Redis/database checks and a deterministic canonical-CSRF regression. Live Redis 8.10.1
acceptance proves exact role quotas across independent limiter instances and a separate OS process,
worker reconstruction, 140 concurrent requests admitting exactly 120, and shared account lockout.
Disposable PostgreSQL 17 acceptance passed Alembic upgrade/check and least-privilege runtime
registration/login/me/refresh/database health. Ruff lint/format, strict mypy (53 source files), pip
check, backend sdist/wheel build, pip-audit and frontend format/lint/typecheck/80 tests/build/npm audit
PASS. Only the existing frontend chunk-size warning remains. No schema/compose/production secret
change; populated .env files are not committed. Deployed production TLS/proxy/multi-instance smoke
is **not verified** and remains the sole operator acceptance gate.

**Regression hardening:** A full-suite run exposed an existing intermittent CSRF tampering-test
failure: noncanonical base64 pad bits could decode to the same signature. Canonical round-trip
validation now rejects those variants without changing generated valid tokens or the HMAC/CSRF
architecture; the original test is retained and a deterministic pad-bit test was added.


## Cross-reference occurrences outside extracted headings

- Legacy line 1122: > Phase numbers group parallel workstreams; they are not the canonical single-developer execution sequence. **PART 24 — NEW MASTER IMPLEMENTATION ORDER is authoritative.** The Frontend completion and AUTH-ARCH-001 gates, BE-001 through BE-016, AUTH-007 through AUTH-019, AUTH-004/005/006 and AUTH-021/022/023 are recorded complete; AUTH-020 implementation/local/live acceptance are verified with its production operator gate pending. AUTH-024 backend/live and combined frontend/cache acceptance PASS. FE-021, FE-022, FE-023, FE-025, FE-026, FE-027, FE-028, FE-029, FE-038, FE-039, ADMIN-001 through ADMIN-005, EVT-001 through EVT-004, EVT-008, EVT-010 and EVS-003 are complete; MATCH-001 is the next READY development task under the 2026-09-22 demo-priority override. From FE-022 onward, implement/commit/push directly on main unless actual repository protection prevents it. Parts 18/18A remain execution evidence, not a request to redo completed UI. FE-014 builds against the approved API contract with a development-only mock, while EVS-001 through EVS-007, ADMIN-SLIDER-001 through ADMIN-SLIDER-004, and FE-014B later activate end-to-end Admin-managed production content.
- Legacy line 1324: | AUTH-020 | Create rate limiting middleware (slowapi) — Implemented; local/live acceptance PASS; production operator gate pending | 2 | BE-001 | P0 |
- Legacy line 2169: TTL and AUTH-020 production operator gate are unchanged. Gemini remains
- Legacy line 3799: **Next Task**: \`AUTH-020 — Create rate limiting middleware (slowapi)\`.
- Legacy line 3845:   tests PASS on Python 3.14 and 3.12**, including AUTH-020 shared Redis regression. Real row-lock
- Legacy line 3863: - Production Redis/TLS/trusted-ingress/deployed smoke remains **not verified** (AUTH-020). Gemini
- Legacy line 4275: Gate: AUTH-020                Implemented; local/live acceptance PASS; production Redis/TLS/ingress smoke pending [P0; Phase 5]
- Legacy line 4399: **Next development task: MATCH-001 — Create Match model and persistence constraints. Dependency BE-010 is DONE and the local Profile/runtime prerequisite has passed, so MATCH-001 is READY. AUTH-020 production acceptance remains pending operator-provided Redis/TLS/ingress configuration and is a deployment gate, not a blocker for local Matching development. Continue the direct-to-main workflow; execute MATCH-001 only when explicitly requested.**
- Legacy line 4619: frontend chunk advisory, AUTH-020 production operator gate and Gemini remediation remain pending.
- Legacy line 4757: backend current-role authorization remains independent. Copied-access TTL and AUTH-020 production
- Legacy line 4855: Production release still requires AUTH-020 operator configuration/smoke; Gemini remediation pending.
- Legacy line 4889: skew remains AUTH-017's contract. AUTH-020 production Redis/TLS/ingress acceptance and legacy Gemini
- Legacy line 4930: browser error console empty. Existing bundle advisory and AUTH-020 production operator gate remain.
- Legacy line 4967: empty. Existing bundle advisory and AUTH-020 production operator gate remain pending.
- Legacy line 5004: live cases remain unconfigured. Existing bundle advisory and AUTH-020 production operator gate remain.
- Legacy line 5062: profile/readiness/onboarding/matching; AUTH-020 production operator gate; deployment.
- Legacy line 5117: readiness/onboarding/events/sliders, AUTH-020 production Redis/TLS/ingress operator gate and deployment.
- Legacy line 5208: audit implementation, AUTH-020 production operator gate and deployment.
- Legacy line 6851: | EMAIL-002 (**Done 2026-09-24**) | Request/resend verification | EMAIL-001A, MAIL-001, AUTH-020 | Current address only; rate-limited; old token superseded | API/rate/concurrency tests |
- Legacy line 6938: - **Dependencies / ownership:** EMAIL-001A, MAIL-001, AUTH-020; Backend.
