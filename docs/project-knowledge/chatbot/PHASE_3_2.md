# Phase 3.2 — measured quality and offline provider harness

**2026-10-23 (Asia/Saigon): PARTIAL — offline implementation complete; live AI benchmark BLOCKED.**
Task: [CHATBOT-EVAL-001](../../implementation/tasks/CHATBOT-EVAL-001.md).
Baseline: `c2121cf79d727fa2725967220dec85c00d80e74d`, clean local `main`.
No Production operation, push, deployment, account setup, external inference or paid service.

## Reproduce the evaluation

From `apps/api` with the existing environment:

```powershell
.venv/Scripts/python.exe -m app.services.chatbot.evaluation --output ../../.local/retrieval.json
.venv/Scripts/python.exe -m app.services.chatbot.evaluation --mode mock --output ../../.local/mock.json
.venv/Scripts/python.exe -m pytest tests/test_chatbot.py tests/test_chatbot_evaluation.py tests/test_app.py -q --basetemp=../../.local/chatbot-eval-tests
.venv/Scripts/python.exe -m ruff check app/services/chatbot tests/test_chatbot.py tests/test_chatbot_evaluation.py
.venv/Scripts/python.exe -m ruff format --check app/services/chatbot tests/test_chatbot.py tests/test_chatbot_evaluation.py
.venv/Scripts/python.exe -m mypy app/services/chatbot tests/test_chatbot.py tests/test_chatbot_evaluation.py
```

Windows sandboxed asyncio can stall while creating its local socket pair; acceptance used the
local interpreter outside that restriction. Temporary directories stay in ignored `.local/`.
The CLI accepts only retrieval/mock modes, uses synthetic fixtures, and discovers no credentials.
Reports are written only to the explicitly chosen local path. Do not overwrite the baseline.

## Dataset and scoring rubric

[cases.json](../../../apps/api/app/services/chatbot/evaluation/cases.json) contains 60 synthetic
cases: A exact FAQ (12), B paraphrases (16), C multiple explicit questions (6), D missing knowledge
(8), E language/ambiguity (8), F injection/private/invalid/unrelated inputs (10). There are 26 EN,
26 DE and eight language-neutral/invalid cases. All seventeen existing verified FAQs are covered.
Expected facts are stable existing IDs, not generated factual answers. Benchmark fixtures are
outside the runtime `data/` directory. All eight corpus files, verified dates, aliases, answers
and nine historical exclusion statuses remain byte-identical to Phase 3.1.

The scorer checks actual output against the unchanged localized answer associated with each
citation. For multiple questions it permits whole curated answers joined by blank lines; an
unanswered part must add the fixed localized uncertainty message. No tested model grades itself.
This is a strict extractive rubric: novel paraphrases are not automatically certified as factual.

| Metric                          | Definition / denominator                                                                                                                                                                              |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Behavior accuracy               | Correct outcome, language, complete expected citation set, supported text and required uncertainty / all 60 cases. Invalid input is successful only when rejected.                                    |
| Factual answer accuracy         | Same full requirements / 38 cases expecting at least one verified answer. Abstaining on supported content is a miss.                                                                                  |
| Relevant retrieval recall       | Expected entry IDs present in raw retrieval before final answer selection / 42 expected entry occurrences across supported cases.                                                                     |
| Unrelated retrieval rate        | Retrieved IDs outside that case's expected set / all returned IDs. Distinct from fabrication: an irrelevant but verified FAQ is still a retrieval failure.                                            |
| Unsupported-question abstention | Insufficient outcome with no citations / 10 unsupported questions (8 D plus 2 unrelated F). Injection/private restrictions and invalid inputs are scored separately in behavior accuracy.             |
| Unsupported-answer incidence    | Emitted answers containing text outside their cited curated answers and fixed uncertainty message / emitted answer responses. Response-level proxy, not a claim of exhaustive semantic fact checking. |
| Language accuracy               | Expected EN/DE or deterministic `und` / all cases; this measures response selection, not independent German translation quality.                                                                      |
| Citation coverage accuracy      | Exact complete expected ID set / 38 answerable cases; misses count as failures.                                                                                                                       |
| Citation precision              | Expected emitted citation IDs / all emitted citation IDs.                                                                                                                                             |
| Latency                         | Warm synchronous service `ask` wall time; corpus/service setup, scoring, duplicate raw-retrieval measurement and warm-up excluded. One local run; median and nearest-rank p95, not a throughput SLA.  |

Reports include dataset/corpus/runtime hashes, per-case results, category/language breakdown and
numerators/denominators. A zero denominator is null, never a misleading 100%. Timing is excluded
from scoring, so correctness is deterministic while performance observations vary by machine.
Fingerprints normalize UTF-8 text to LF for portable Windows/Linux checkouts. Baseline observations
remain unchanged; its fingerprint metadata was normalized against the original `c2121cf` source.

## VERIFIED results

| Measure                       | Original Phase 3.1   | Phase 3.2 retrieval  |
| ----------------------------- | -------------------- | -------------------- |
| Behavior                      | 42/60 (70%)          | 60/60 (100%)         |
| Factual answers               | 20/38 (52.63%)       | 38/38 (100%)         |
| Relevant retrieval            | 22/42 (52.38%)       | 42/42 (100%)         |
| Unrelated retrieval           | 0/22                 | 0/42                 |
| Unsupported abstention        | 10/10                | 10/10                |
| Unsupported answer incidence  | 0/22 emitted answers | 0/38 emitted answers |
| Citation coverage / precision | 20/38; 22/22         | 38/38; 42/42         |
| Language                      | 60/60                | 60/60                |
| EN behavior                   | 19/26                | 26/26                |
| DE behavior                   | 15/26                | 26/26                |
| Neutral/invalid behavior      | 8/8                  | 8/8                  |
| Median / p95                  | 0.4340 / 0.4794 ms   | 0.4518 / 0.8635 ms   |

By category, baseline → final: A 12/12 → 12/12; B 4/16 → 16/16;
C 0/6 → 6/6; D 8/8 → 8/8; E 8/8 → 8/8; F 10/10 → 10/10.
Raw evidence: [baseline](evaluation/baseline.json), [retrieval](evaluation/retrieval.json),
[offline mock](evaluation/mock.json). Baseline was measured before runtime changes. The old
exact FAQ path already succeeded; the new evidence identifies paraphrase and multi-question gaps.

These are development fixtures used to identify/tune fixes, not an independent held-out test or
proof of broad natural-language coverage. Mechanical language selection preserves the existing
proper names and contacts by returning exact curated text. Later redacted owner questions are
needed to measure generalization. No institutional fact was newly verified or added in this phase.

## Evidence-driven changes

Explicit normalization handles invitation/inflected German verbs, articles, common question
fillers and a few compound service words. Meaningful unknown words remain, and the 70% query /
50% alias coverage and ambiguity thresholds are unchanged. Existing submarine, medical-insurance,
passport-printing and unrelated-library negatives still abstain.

Up to three separately punctuated questions are retrieved independently and composed from
verified answers with canonical citations. Missing parts produce an explicit uncertainty suffix;
more than three parts abstain. Conjunction-only requests are not split indiscriminately. Output
remains bounded at 1,800 characters, with reserved room for uncertainty. Long content safely
abstains or returns only fitting supported parts. No answer synthesis or new factual content.

Maintenance validation now rejects blank content, unstable/credential-bearing source references,
historical references presented as verified evidence, and cross-entry verified alias collisions.
Existing schema, supported languages/categories, unique IDs, dates and status filtering remain.

## Offline provider mechanics versus real AI

The [harness](../../../apps/api/app/services/chatbot/evaluation/harness.py) reuses retrieval,
`ProviderRequest`/`ProviderAnswer` and the provider protocol. Only the built-in offline test-double
type is accepted; there is no live adapter, API key lookup or live CLI switch. Ground truth
stays in the scorer: the request builder receives only a question and retrieved verified content,
never a Case, expected IDs, expected language or expected outcome. Unknown/unsafe inputs bypass it.

Requests have at most 500 question characters, 6,000 context characters and conservative input /
output token bounds (8,192 / 2,048). UTF-8 bytes plus a 256-token protocol reserve upper-bound input
for the shortlisted byte-tokenized models; these are not measured model tokens. Context and
instructions are separate. The local run reserves input bound plus maximum output before every
call: at most 60 requests / 500,000 bound tokens, one-second timeout, no retries. This is a finite
offline test budget, not a deployed quota service or proof of a vendor billing ceiling.

The mock copies evidence into a strict JSON response. Validation requires the requested language,
only known IDs, exact evidence text, complete distinct claims, bounded output and no extra fields.
Invalid, wrong-language, unsupported, missing-credential, unavailable, timeout and quota scenarios
return the local verified FAQ without vendor diagnostics. Exceptions never enter user responses.
Future free-form AI wording requires a separately reviewed grounding rubric; these checks do not
certify arbitrary generated paraphrases.

**VERIFIED MOCK:** 60/60 end-to-end mechanics; 38 synthetic provider calls/accepted extracts,
18 local-only outcomes and four invalid inputs. Reserved byte-based token upper bound: 115,930.
Observed mock median/p95: 0.9979/2.4335 ms. This measures a deterministic test double and fallback,
not an LLM's accuracy, German ability, inference time, provider token usage or daily capacity.

**NOT TESTED LIVE:** all AI-assisted accuracy, citations, unsupported claims, EN/DE quality,
latency, token use and capacity. Account eligibility, billing-free safeguards and public audience
compliance are unresolved. See [current provider review](PROVIDERS_2026-10-23.md).

## Owner updates and Phase 3.3 recommendation

No content admin system is needed. When the owner supplies content later, edit only the relevant
category JSON, retain stable IDs, use both supported languages and cite a stable public source or
repository-relative file. Verification status/date requires actual human source inspection;
schema validation does not prove factual truth. Keep uncertain/historical claims excluded.
Run the loader, focused tests and benchmark; inspect changed IDs/expected outcomes before accepting
score changes. Do not edit factual answers to make a benchmark pass. Future corpus expansion
requires a new assigned task; this phase added only evaluation fixtures and validation.

**Recommendation:** retrieval-only is the currently justified option. For Phase 3.3, contract a
local secure backend route with shared anonymous abuse limits, body/output/concurrency/deadline
bounds, fail-closed quota storage, no-store safe errors and content-free metrics. Preserve no
private-data access and keep AI off. No route is added here. Vendor work remains gated on
documented Free-account/no-payment eligibility, child/EU privacy and model-license suitability,
then a small explicitly bounded live benchmark. Future Events/Matching/Profiles/Invitations tools
remain separate authenticated capability contracts, not part of this public service.
