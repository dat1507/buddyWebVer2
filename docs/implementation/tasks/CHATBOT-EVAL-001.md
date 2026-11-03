# CHATBOT-EVAL-001 — Phase 3.2 evaluation and provider feasibility

**Assigned:** 2026-10-23 (Asia/Saigon), explicit pasted owner request.
**Status:** PARTIAL — OFFLINE COMPLETE / LIVE AI BENCHMARK BLOCKED.
**Baseline:** clean `main` at `c2121cf79d727fa2725967220dec85c00d80e74d`.

Implement 40–60 synthetic EN/DE benchmark cases, explicit metrics and reproducible baseline/final
reports; a provider-protocol-compatible offline/mock harness with grounding, bounds, timeout/quota
and failure fallback; evidence-driven retrieval fixes; current official Cloudflare/Gemini review;
focused tests and maintenance/Phase 3.3 guidance. Preserve every corpus file byte-for-byte.
No knowledge expansion, institutional web research, public API/UI, private tools, new dependencies,
migrations, account/billing/cloud changes, push or deployment. Live inference only if all owner
conditions are verified; otherwise finish offline work and report PARTIAL with precise blockers.

Focused source: existing `app/services/chatbot`, new evaluation package and tests under `apps/api`,
package-data declaration only if needed. Existing test/CLI/config contracts are inspected, not
refactored. Documentation: chatbot knowledge guides, this task and control-plane/index/validation.
Regression: existing chatbot suite when behavior changes; app smoke; Ruff/format/mypy; benchmark
determinism, source-traceability, no answer-key leakage, mock/live separation, no network/private
access; corpus immutability, package-data and task/link coverage. No completed unrelated gates rerun.

## Verified local outcome — 2026-10-23

Implemented the separate 60-case synthetic EN/DE dataset, baseline/final scoring and raw reports,
offline provider-protocol harness, bounded multi-question responses and targeted lexical fixes.
Added source/alias maintenance validation without editing any corpus bytes, facts, aliases, dates
or exclusion status. All 17 verified FAQs and nine excluded historical summaries remain intact.

Baseline behavior 42/60 → final 60/60; EN 19/26 → 26/26, DE 15/26 → 26/26, neutral/invalid
8/8 both. Factual answers 20/38 → 38/38; relevant raw retrieval 22/42 → 42/42; unsupported
abstention 10/10 both; no unrelated retrieval or unsupported additions in observed answer output.
Final citation coverage 38/38 and precision 42/42. Warm service median/p95 0.4518/0.8635 ms.
Development-set tuning is explicit; no held-out or natural-language generalization claim.

Mock mechanics: 38 provider calls accepted, 18 local outcomes, four invalid requests; 60/60
end-to-end behavior. Mock timing/byte-based reservations are not LLM performance/token evidence.
Failure scenarios cover missing credentials, unavailable/disabled provider, quota, timeout,
malformed/wrong-language/untrusted output, bad citations, request budgets and safe FAQ fallback.
No live adapter or live CLI option exists. Expected-case fields never enter provider requests.

Official provider review: Cloudflare remains a conditional candidate, NOT APPROVED for public
integration. Free-account/payment-free entitlement, child/EU privacy and exact license obligations
remain unresolved. Gemini Free retains the documented public-minor/EU restrictions. No account,
credential, external inference, billing, cloud setup, database, Production, push or deployment use.
Live comparison is NOT TESTED; overall Phase 3.2 is PARTIAL as the owner request requires.

Evidence and metric denominators: [Phase 3.2 record](../../project-knowledge/chatbot/PHASE_3_2.md),
[dated provider decision](../../project-knowledge/chatbot/PROVIDERS_2026-10-23.md).

Validation on the existing Python 3.14.0 environment:

- `python -m pytest tests/test_chatbot.py tests/test_chatbot_evaluation.py tests/test_app.py -q`
  with workspace-local basetemp, outside the known Windows asyncio sandbox restriction:
  **234 PASS** (145 prior chatbot cases, 87 evaluation/harness cases, two app smoke tests).
- Ruff check and format check on service and both test modules: **PASS**.
- Strict mypy on service and both test modules: **PASS**, 15 checked source files.
- After a final report-fingerprint portability fix, the 87 evaluation/harness tests were rerun:
  **87 PASS**, including equal fingerprints for LF/CRLF. Original baseline scores were retained.
- Retrieval/mock CLI reports: **PASS**, score results and mock/live separation recorded above.
- Wheel build without isolation plus extracted-wheel evaluation CLI: **PASS**; eight corpus JSON
  files and the separate 60-case fixture are packaged. No dependency/lock change.
- Python-canonical evaluation JSON, focused Markdown formatting, corpus hashes, source/task links,
  236-file index coverage, scope/security review and `git diff --check`: **PASS**.

No frontend/shared domain source changed; full backend/frontend regression and live provider tests
were not run. No previous accepted feature gates were repeated beyond chatbot regression and app
smoke justified by the changed service/package. Local `main` commit only; hash is in final response.

Continuation: no executable task assigned. Phase 3.3 should first contract secure retrieval-only
backend access/abuse/deadline/quota controls, keeping AI disabled. Live Phase 3.2 evidence still
requires Free-only account entitlement/no-payment proof, institutional child/EU/privacy/license
review, and a predefined small synthetic benchmark with enforced consumption ceilings.
