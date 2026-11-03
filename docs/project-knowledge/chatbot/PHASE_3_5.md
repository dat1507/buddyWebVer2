# Phase 3.5 — chatbot readiness and security validation

## Phase3.5.1 continuation —2026-11-03

[Current integration/gate report](PHASE_3_5_1.md) supersedes the old integration/Linux blocker below:
approvedc64 plus chatbot is isolated on codex/chatbot-phase35-integration; priora1aa is protected.
Actual Python3.12 Linux image and integration regressions are locally verified. **Production NO-GO**:
actual hosted proxy/logging and exact candidate CI/deployment remain unverified. Original records
below describe their completed historical snapshots; do not rerun them merely for documentation.

2026-11-01 (Asia/Saigon), [CHATBOT-READY-001](../../implementation/tasks/CHATBOT-READY-001.md).
**Local review complete; RELEASE NO-GO.** This is not Production acceptance or authorization.

## Boundary and evidence

Primary checkout: unrelated dirty `codex/pillow-security-fix` at `8c02dfb`. Local main remains
`9ec31fbcf0aadfb5347bd9eba76c2f362b205904`; fresh read-only `git ls-remote` confirms remote main
`5a7bb90d7099ffdc2de82897dd41a1f86b5fabbf`. Main diverges **6 local / 4 remote commits**.
This work uses a separate detached main 9ec checkout. No merge/reset/rebase/branch movement occurred.
Primary dirty files, staging and all existing worktrees are preserved; task changes are isolated.

Fresh Vercel connector metadata: `buddy-web-ver2`, Vite/Node 24, Production READY deployment
`dpl_EU19m7DJSsrbHNc2CvAZVX53LusX`, main 5a, public domains assigned. The primary checkout's dated
2026-11-01 release record reports Render 642fc11/AutoDeployOFF and the absolute Production API URL.
That is retained owner evidence, not a fresh Render command/env/runtime/log inspection here.
No Production chatbot request, authenticated cloud test, deployment or configuration mutation ran.

**Integration blocker:** this old chatbot snapshot lacks already released Pillow 13/Zod 4.6.6 and
newer UI/development dependency changes. Remote pyproject also lacks chatbot package-data rules.
Do not deploy this detached tree, replace remote main with it, or restore its old dependency locks.
Integrate only reviewed chatbot/readiness changes onto an explicitly approved current baseline,
preserving all newer security/UI changes, then validate the exact combined release artifact and CI.

## Narrow changes

- Docker Uvicorn CMD adds `--no-access-log`: raw request targets can otherwise disclose a rejected
  query string. The existing structured app logger retains status, generated request ID, route
  template and duration; it accepts no body/question/cookie/token fields. Proxy settings are unchanged.
- CLI stdin/stdout/stderr explicitly use UTF-8. Wheel verification exposed German UTF-8 input being
  decoded as a Windows legacy encoding. Invalid UTF-8 now exits2 with a generic diagnostic.
- Focused tests add actual Uvicorn trusted/untrusted/multi-hop/IPv6 header cases, bucket capacity/TTL,
  independent runtime counts, restart-only flag behavior, rejection-log privacy, container access-log
  configuration, CLI encoding/error cases and literal HTML rendering in questions/answers/citations.
- No UI redesign, app authentication change, database migration, dependency upgrade or knowledge edit.

## Configuration and operational limits

| Setting | Repository behavior / operator requirement |
| --- | --- |
| Frontend API | Existing requestJson appends `/chatbot/query` to VITE_API_URL ending `/api`; Production uses direct HTTPS Render API, not a new Vercel proxy. Vercel's SPA rewrite is not an API proxy. Local built artifacts use `http://127.0.0.1:8025/api`. |
| CORS/session | Exact configured origins, POST/content-type preflight, Retry-After exposed. Chatbot's one stateless POST omits cookies/CSRF; signed-in callers receive the same public data. Other transport paths keep their existing credential/CSRF behavior. |
| Frontend flag | Exact `VITE_CHATBOT_ENABLED=true`; missing/false/invalid values hide UI. Vite compiles it at build time: changing hosted env needs a new build/deployment. |
| Backend flag | CHATBOT_API_ENABLED defaults false; settings are cached per process. Env changes require a controlled process restart/redeploy; they are not an instant in-memory kill switch. Disabled returns 503/disabled while liveness remains200. |
| AI | CHATBOT_AI_ENABLED defaults false and is constrained to Literal[False]; true/invalid config fails closed. No provider is called in any frontend/backend flag combination. |
| Proxy | Docker explicitly trusts only 127.0.0.1. App uses normalized ASGI client peer, never raw XFF/Forwarded/X-Real-IP. Confirm actual ingress peers, hop chain and sanitization before changing the allowlist. Never copy `*` or pick the leftmost user header. |
| Worker count | Docker does not set --workers; confirm WEB_CONCURRENCY/start overrides and actual instance count. Local simulation explicitly uses one worker. Each process has independent quotas, slots and source snapshots. |
| Quotas | Defaults:30/client/60s,300/process/60s,2048 client buckets,2 processing slots. Expired buckets are removed; live buckets are not evicted to reset quotas. Equivalent IPv6/IPv4-mapped forms share identity; unknown peers share a bucket. NAT users share an IP quota; IPv6 rotation/distributed abuse is not defeated. |
| Bounds |500 Unicode characters,4096 body bytes,2000 ms deadline,16384 serialized response bytes. Malformed/oversized/error requests consume admission. Queued/running work is bounded by retained slots. |
| Timeout/restart | A timeout cannot kill running synchronous work; its slot remains held until completion. Counts reset on restart and multiply across processes. No claim of distributed enforcement or unrestricted abuse resistance. |
| Expected load | Retain simple in-memory design for the approximate100 questions/day scope; measured local bounds support this choice. Hosting topology, shared-NAT usability and operational acceptance still need confirmation. No new Redis/service is provisioned. |
| Logging | New container command disables Uvicorn raw access logs; structured app metadata remains. Actual Render start overrides, platform/edge access logs, retention and query redaction remain UNVERIFIED. |

[Uvicorn settings](https://www.uvicorn.org/) document forwarding allowlists and access-log controls.
[Render's FastAPI guidance](https://render.com/articles/fastapi-production-best-practices) recommends
restricted proxy trust; its generic guidance does not establish this service's actual trusted chain.
No change to forwarding behavior was justified by current environment evidence.

## Runtime and knowledge artifact

Repository Docker/CI target Python 3.12. Tests ran on **Windows CPython 3.12.10**, FastAPI 0.141.1,
Pydantic 2.13.5/Uvicorn 0.53.0. All **37 runtime pins match** this snapshot's requirements.lock;
pip check PASS. All438 installed frontend packages match the snapshot lock (zero mismatches/missing
nonoptional packages); Node 24.11.0. Existing packages were reused without downloads/install upgrades.
Docker daemon was unavailable: no current Linux/container build/run or exact hosted compatibility
is claimed. Candidate dependency declarations are stale relative to current security releases.

Wheel build and extraction PASS. All chatbot modules, nine JSON files and canonical source match
checkout bytes; loader resolves module-relative paths from an unrelated cwd. Two independent CLI
processes report identical source hashes; five packaged EN/DE/verified/owner/conflict/miss queries pass.
Canonical hash `0fe1c16900d47c2c57e50d56cdc3ee4b2bd66dc9d6b2ccd2366256162519f0a8`,22129 bytes,
431 lines,174 passages (147 owner,6 conflicted,17 sensitive,4 instruction). All factual source/JSON/
intent vocabulary bytes are unchanged. Owner authorization never becomes official verification.

Existing reload tests pass: add/edit/delete, same-size/mtime edits, invalid/missing recovery, no stale
manual fallback, concurrent immutable snapshots and unchanged-version parse caching. Source loading
uses read-only file opens and in-memory indexes; writable persistent storage is not required. Each
process observes a new version on its next guide lookup; in-flight requests can retain an earlier
coherent snapshot. There is no cross-process simultaneous cutover guarantee. Production source
updates and rollbacks require a reviewed deployment artifact; local edits do not reach Render.
German guide quotations remain explicitly untranslated; deterministic intent/conflict limits persist.

## Executed local acceptance

Final backend non-live regression: **1851 PASS**,79.89s, one existing AnyIO/Starlette deprecation.
Earlier203 focused/1847 pre-CLI-fix results and final7 CLI cases are subsets/checkpoints, not added
to this total. Ruff/changed format/strict mypy 129 files PASS. Frontend **101 PASS /4 files**,
27.87s; TypeScript/affected ESLint/Prettier, ON/OFF builds PASS. Existing large-entry warning remains.

Built Vite previews 5195/5196 -> packaged wheel API 8025 -> default source -> actual UI PASS:
verified registration, EN food, DE laundry/untranslated qualification, line/hash citations, unsupported
Mars question, real429/cooldown/disabled retry and real503/unavailable. All four frontend/backend flag
combinations checked: OFF/OFF hidden+503; ON/OFF friendly unavailable; OFF/ON hidden; ON/ON retrieval.
Synthetic authenticated/public parity, invalid inputs/encoding, source injection/conflicts/high-stakes,
quotas/timeout/cancellation/oversized output and no-provider/private-DB contracts pass in pytest.

Bounded36-request local load:22x200,1x400,2x422,1x413,4x503 concurrency rejection,6x429. Eight concurrent
chatbot attempts plus four concurrent liveness requests: health 4/4 x200, slowest469.16 ms;
chatbot sample p95 468.91 ms; process CPU delta 1.6562 s, working set113135616 bytes, peak113782784 bytes.
These are one Windows sample, not Linux capacity estimates or unrestricted public-abuse acceptance.
A separate four-request/two-OS-process check yielded200 then429 independently in each process for
the same loopback client, with identical canonical hashes. Restart resets were observed during mode
changes. Application external/provider/private-DB guard counts remained zero. Real app/Uvicorn logs
exclude synthetic body/query markers; raw access targets are absent. All owned servers stopped.

Actual EN/DE1440/768/390/320 px browser bounds, input/header visibility and source wrapping inspected;
chat panel has no horizontal overflow. At320 px the old snapshot's German Landing document is329 px
with both ON and OFF builds; this is not attributable to the chatbot and says nothing about the
newer Production UI. Mobile dialog isolates background, hides expanded launcher and traps native
Tab/Shift+Tab; Escape restores launcher focus and clears inert/body lock. Actual emulated reduced
motion gives animation duration 0s. Viewport/media overrides restored. Desktop/mobile screenshots
inspected; one initial screenshot capture clipped its header despite headerTop0/scrollTop0, corrected
with an accurate settled viewport capture. No physical-device keyboard/hardware SR/full WCAG claim.

## Release gate matrix

| Gate | Status | Evidence / remaining boundary |
| --- | --- | --- |
| Backend runtime | UNVERIFIED | Local3.12 PASS; final integrated Linux image/hosted runtime not tested. |
| API routing | UNVERIFIED | Local built direct-base path/CORS PASS; final deployed chat route/combined config pending. |
| Trusted proxy | UNVERIFIED | Representative Uvicorn tests PASS; actual peers/hops/sanitization not established. Critical. |
| Rate limiting | PASS (local) | Client/global/TTL/capacity/concurrency/restart/two-process checks; per-process/NAT limits documented, operator topology acceptance pending. |
| Resource protection | PASS (local) | Existing bounds/deadline/retained slots/response guard and modest load. No arbitrary abuse guarantee. |
| Knowledge artifact | PASS (local) | Exact wheel/source/JSON hash,174 passages, unrelated cwd/two processes; integrated image must repeat. |
| Knowledge provenance | PASS | Verified/owner/conflicted states and actual source lines/hash retained; no new facts. |
| Privacy/logging | UNVERIFIED | Local leak fixed/tested; hosted command/edge logs and retention require acceptance. Critical. |
| Feature flags | PASS (local) | All four built combinations and restart-only backend disablement. Actual release env values unverified. |
| AI isolation | PASS | Hard OFF/no external provider calls; no new inference dependency. |
| Frontend | PASS (local) | Built UI101 tests and responsive/source/error flow; combined current-UI artifact still required. |
| Accessibility | UNVERIFIED | Local keyboard/modal/reduced-motion checks PASS; hardware SR/physical mobile keyboard manual. |
| Regression | PASS (local) |1851 backend/101 frontend, static/build/wheel; no exact integrated hosted CI exists yet. |
| Cost | PASS (scope) | No service/billing/dependency provisioned. Future release must confirm existing Free account limits. |
| Rollback | UNVERIFIED | Runbook prepared; existing retained targets from dated evidence must be reconfirmed before release. |
| Git/release integrity | FAIL | Divergent histories and missing newer security/UI updates in this snapshot; no approved integrated SHA. |

**Decision: NO-GO.** Resolve critical Git/security integration, exact Linux artifact, trusted proxy,
routing/configuration and hosted logging gates before Phase 3.6. Manual device/SR items alone would
not explain this decision. Read the [Phase 3.6 runbook](PHASE_3_6_RUNBOOK.md), [test commands](PHASE_3_5_COMMANDS.md)
and [owner guide](OWNER_GUIDE.md). No remote release operation is authorized by this report.
