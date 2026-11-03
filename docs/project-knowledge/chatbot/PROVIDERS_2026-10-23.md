# Provider decision — 2026-10-23

**PARTIAL / NOT APPROVED for public AI integration.** Local retrieval and offline mechanics are
verified; live AI quality is NOT TESTED. All sources below were accessed 2026-10-23. This is a
technical suitability review with explicit unresolved compliance gates, not institutional legal
approval. No external account or credential was inspected, created or configured.

## Cloudflare cost and account gate

**VERIFIED DOCUMENTATION:** [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
provides 10,000 neurons/day on Workers Free; reset is 00:00 UTC and exhaustion produces errors.
Paid Workers can incur overage. Certain named models require paid billing or prepaid Gateway
credits. A documented Free allocation is not evidence that this owner's account/model is eligible
without a payment method. That account-specific condition remains **BLOCKED / UNVERIFIED**.

[Limits](https://developers.cloudflare.com/workers-ai/platform/limits/) gives ordinary text
generation 300 requests/minute, with distinct limits for paid-only models. Rate and daily compute
quotas are separate; documentation and model-specific exceptions can change. No observed rate
or availability is claimed. The [REST guide](https://developers.cloudflare.com/workers-ai/get-started/rest-api/)
supports server-side FastAPI integration through an account-scoped HTTPS request and server token,
without deploying a Worker. No such adapter or token configuration is implemented.

Strict zero-cost configuration would require documented account Free status, no Paid plan/credits/
paid-model routing, a fixed eligible model, shared daily reservation, request/output caps and
immediate FAQ fallback. On Paid, an application-only quota is not an account billing guarantee.
No payment method, billing activation or automatic upgrade is acceptable for this project.

## Two documented candidates, not measured model recommendations

| Exact model ID                       | Availability evidence / intended comparison                                                                                                                                                                |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `@cf/meta/llama-3.2-1b-instruct`     | [Cloudflare model page](https://developers.cloudflare.com/workers-ai/models/llama-3.2-1b-instruct/) exists; small multilingual instruction model, primary conditional low-consumption benchmark candidate. |
| `@cf/meta/llama-3.1-8b-instruct-fp8` | [Cloudflare model page](https://developers.cloudflare.com/workers-ai/models/llama-3.1-8b-instruct-fp8/) exists; quantized instruction model, conditional quality comparator if justified.                  |

The [Meta 3.2 card](https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_2/MODEL_CARD.md)
and [Meta 3.1 card](https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_1/MODEL_CARD.md)
include English and German among supported languages and describe assistant/retrieval use cases.
That does not establish grounding, instruction-following, quantized German quality or latency on
BuddyWeb. All are **NOT TESTED**. Pricing inclusion/model-page availability are documentation-only
evidence, not account entitlement. No large/new model is selected merely for size or recency.

## Privacy, minors, EU and licenses

**VERIFIED DOCUMENTATION:** [Workers AI data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/)
says Customer Content is not used for training. Standard stateless requests have no retention
after processing, with legal/security exceptions. Stateful features, application/Gateway logging,
caching and third parties can retain content; operational metadata may remain. Anonymous visitors
can type personal data, so a public corpus does not make inference anonymous or automatically safe.

[Workers AI service terms](https://www.cloudflare.com/service-specific-terms-developer-platform/)
place responsibility for output/actions and third-party/model rights on the customer. The
[self-serve agreement](https://www.cloudflare.com/terms/) and these terms did not establish a
project-specific approval to serve possible minors. **UNRESOLVED:** contracting authority,
under-18 educational use, notice/consent and child-data safeguards. Silence is not permission.

The [Cloudflare DPA](https://www.cloudflare.com/cloudflare-customer-dpa/) anticipates processing
outside the EEA and describes transfer safeguards. It is not a guarantee of EU-only inference.
**UNRESOLVED:** institutional controller/processor arrangements, applicable lawful basis, privacy
notice, subprocessor/transfers review, children's data, abuse controls and retention configuration.
No claim of confirmed GDPR compliance or public educational-app approval is made.

The [Llama 3.2 license](https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE)
and [Llama 3.1 license](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE)
are custom community licenses, with attribution/redistribution obligations including the visible
Built with Llama requirement in applicable cases; legal contracting capacity and incorporated use
policies matter. The [3.2 AUP](https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_2/USE_POLICY.md)
and [3.1 AUP](https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_1/USE_POLICY.md)
restrict harmful/unlawful uses, including harm to children and unlawful disclosures. Serving an
educational FAQ does not by itself prove every license/AUP obligation is satisfied. Determine
the requirements for the proposed hosted service and document owner/institutional acceptance
before enabling a model. No license compliance approval is inferred from catalog availability.

## ESTIMATED capacity, not observed support for 100 questions/day

Assumptions: 100 daily questions, 400 prompt/question tokens plus 1,000 retrieved-context tokens,
250 output tokens per AI call; either all calls use AI or 70% are answered locally. No tokenizer
or live usage measurements were made. The pricing table lists per-million input/output neurons:
Llama 3.2 1B = 2,457 / 18,252; Llama 3.1 8B FP8 = 13,778 / 26,128.

| Candidate  | 100 AI calls/day | 30 AI calls/day (70% FAQ-only) |
| ---------- | ---------------- | ------------------------------ |
| 3.2 1B     | ~800 neurons     | ~240 neurons                   |
| 3.1 8B FP8 | ~2,582 neurons   | ~775 neurons                   |

Formula: calls × (input tokens × input coefficient + output tokens × output coefficient) / 1e6.
At the harness's conservative 8,192-input/2,048-output cap, 100 calls could reserve ~5,751
neurons for 1B or ~16,638 for 8B FP8; the latter exceeds the daily Free allocation. These are
illustrative bounds, not entitlement or measured token usage. Shared account consumption, burst
abuse and longer contexts can exhaust quotas. Do not claim live 100-question capacity from
planning assumptions. Retrieval-only uses zero external tokens and no new operating service.

## Gemini comparison and decision

**CONFIRMED RESTRICTIONS:** current [Gemini terms](https://ai.google.dev/gemini-api/terms)
require users to be 18+ and restrict clients likely accessed by under-18s. Clients made available
to EEA/Swiss/UK users must use Paid Services. Unpaid content can be reviewed/used for improvement;
regional data-treatment exceptions do not override the Paid Services restriction. Under the
current public-minor/Germany audience and absolute-zero-cost constraints, Gemini Free is **NOT
APPROVED**. No SDK, adapter, billing setup or inference was added.

| Option         | Recommendation                                                                                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Retrieval-only | Recommended for Phase 3.3's secure backend contract; current verified answers and safe abstention, no external inference/billing/privacy dependency.                          |
| Cloudflare     | Preferred research candidate, NOT APPROVED. Free-only account/model/no-payment evidence, child/EU/privacy/license review, operational caps and live benchmark remain blocked. |
| Gemini Free    | Not suitable under current documented age/EU restrictions and zero-cost public-access requirements.                                                                           |

**LIVE BENCHMARK: NOT TESTED.** No approved account configuration/credentials, payment-free
entitlement or completed compliance review exists in the available evidence. No external call was
attempted. To close this part of Phase 3.2, establish those gates first, then use a predefined small
synthetic subset with fixed call/compute ceilings and independent grounding review. The offline
mock scores cannot substitute for model performance, and no Production AI release is recommended.
