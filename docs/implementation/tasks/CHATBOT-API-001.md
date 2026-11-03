# CHATBOT-API-001 — Phase 3.3 secure retrieval API

**Assigned:** 2026-10-23 (Asia/Saigon), explicit pasted owner request.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.
**Baseline:** clean `main` at `d890fb0840e2196f301d60076c1b427cc1b687ff`.

Implement `POST /api/chatbot/query` for public knowledge, anonymously or with cookies, reusing the
existing service and immutable corpus. Typed request/response; public-only citation projection;
default-OFF API flag, hard-disabled AI; bounded request body, rate state, concurrency, deadline
and output; generic no-store failures and existing redacted telemetry. No auth/private-data tools,
provider calls, frontend, factual edits, database/migration, dependency, paid service, push or deploy.

Focused files: new API/schema/config/protection modules, main router/middleware/lifespan wiring,
chatbot API tests and one superseded no-route chatbot test. Reuse trusted peer normalization and
observability, evaluate existing limiter without changing auth limits. Document process-local
limiter/restart/proxy and non-interruptible worker limitations. Keep Production disabled.

Validation: EN/DE/multi-question/miss, anonymous and synthetic authenticated cookies, citations
without internal paths, malformed/oversized/streaming bodies, injection, spoofed IP headers,
IPv4/IPv6, flags/config failures, limiter capacity/expiry, concurrency/deadline/cancellation,
no provider/DB/network or question logging; prior chatbot and relevant API/security regression;
local HTTP fixture smoke, Ruff/mypy/format, package and corpus/task/link integrity. Final local
commit after verification; no unrelated accepted feature gate repeated.

## Acceptance — 2026-10-23

Implemented the typed public POST route, safe citation projection and default-OFF feature gate.
Anonymous and authenticated cookies use identical verified answers without authentication/private
database dependencies. Reused existing peer normalization, redacted telemetry and CORS. Dedicated
bounded process-local quotas/TTL/capacity, body admission, worker slots/deadline and serialized
output bounds; AI `true` fails closed, no provider credentials or network path added.

Existing local Python 3.14: **68 focused API tests PASS; 1717 non-live backend tests PASS**,
including prior chatbot/evaluation and shared auth/rate-limit/observability/CORS/application tests.
One existing AnyIO/Starlette deprecation warning; live-environment files explicitly excluded.
Ruff app/tests, six changed-file formatting checks and strict mypy on 127 files PASS. Wheel build
and extracted-wheel default-OFF/enabled-DE API PASS; all eight corpus files byte-identical to
`d890fb0` and included unchanged. Actual loopback Uvicorn HTTP: **14 checks PASS**, including a
synthetic authenticated identity, no chatbot DB/provider/external connections; server stopped.
Documentation links/task coverage, legacy archive/scope/secret review and diff checks PASS.

Initial new-fixture assumptions and a disposable package-smoke variable collision were corrected;
no factual/retrieval/auth-domain changes were made to obtain passing results. No Python 3.12,
Docker, live DB/Redis, frontend, deployment or Production acceptance claimed.

Limiter is not distributed and resets on restart; NAT shares buckets, IPv6 rotation remains possible.
Timeout cannot stop Python work: its slot stays occupied until completion. Deployed proxy identity
and platform access-log behavior require verification before a separately authorized public rollout.
Cloudflare/Gemini eligibility/privacy/license and zero-cost gates remain unchanged; no paid service
or new dependency. No push/deploy. Phase 3.4 backend contract is ready; no next task assigned.

Authoritative contract, commands, resource defaults and residual limits:
[Phase 3.3 guide](../../project-knowledge/chatbot/PHASE_3_3.md).
