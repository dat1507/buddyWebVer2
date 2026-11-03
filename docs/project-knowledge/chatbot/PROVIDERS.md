# Provider assessment — checked 2026-10-22

2026-10-23 follow-up: see the [dated current assessment](PROVIDERS_2026-10-23.md) for refreshed
pricing, model/license/age/EU findings and the explicit NOT APPROVED / live NOT TESTED decision.
This earlier assessment is retained as historical evidence.

Decision: **all AI integration disabled**. Local FAQs are the working zero-cost fallback.
Only official public documentation was read. No account, token, billing setup, model execution,
Playground inference or cloud resource was created or accessed. Findings are documentation
evidence, not a legal opinion or confirmation of the owner's account eligibility.

## Cloudflare Workers AI

| Question                    | Finding / project implication                                                                                                                                                                                                                                                                                                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Free allocation / hard stop | [Pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/) documents 10,000 neurons/day, reset at 00:00 UTC, and errors when Free limits are exceeded. Paid Workers charges overage; zero-cost operation requires staying on Free. Some models explicitly require paid billing or prepaid credits. No paid upgrade or credit mechanism is acceptable here.                         |
| Candidate models            | The current pricing table and model pages list [Llama 3.2 1B Instruct](https://developers.cloudflare.com/workers-ai/models/llama-3.2-1b-instruct/) and [Llama 3.1 8B FP8](https://developers.cloudflare.com/workers-ai/models/llama-3.1-8b-instruct-fp8/). These are Free-allocation candidates rather than approved/account-tested models. Recheck the catalog and model license before use.     |
| Billing activation          | Free allocation does not require upgrading to Paid according to pricing. Actual account onboarding/model entitlement and absence of any billing/auto-upgrade path have not been inspected. No credentials or account changes are authorized by this assessment.                                                                                                                                   |
| FastAPI integration         | The [REST guide](https://developers.cloudflare.com/workers-ai/get-started/rest-api/) uses an account-scoped HTTPS model-execution endpoint with a server token. A later asynchronous adapter could call it from the existing API without deploying another Worker. Do not expose account tokens in frontend/URLs/logs; this phase supplies only the protocol.                                     |
| EN/DE                       | Llama 3.2's page describes multilingual dialogue. That is not a measured guarantee for German university guidance. Benchmark both languages for factuality, citations, refusal and latency before choosing model/quantization. No performance was measured here.                                                                                                                                  |
| Privacy / retention         | [Data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/) states no training on Customer Content and no retention after standard stateless inference completes, subject to legal/security exceptions. Stateful features, Gateway logging/caching and connected services can retain content; operational metadata remains. Do not equate this with universal zero retention. |
| Under 18                    | The inspected [self-serve agreement](https://www.cloudflare.com/terms/) and data page did not establish a clear public student-chatbot permission for under-18 users. Resolve contracting eligibility, application audience and exact model license/AUP with the responsible reviewer before inference. Absence of an observed ban is not approval.                                               |
| Germany / EU                | The [customer DPA](https://www.cloudflare.com/cloudflare-customer-dpa/) describes EU transfer safeguards/SCCs where applicable. This does not establish EU-only processing or project compliance. Review controller/processor roles, transfers/subprocessors, privacy notice, lawful basis, data minimization and children's-data handling with the responsible institutional reviewer.           |

Capacity estimate, not an entitlement: the pricing table lists 13,778 input and 26,128 output
neurons per million tokens for Llama 3.1 8B FP8. At assumed 1,000 input + 200 output tokens,
100 questions would use about 1,900 neurons/day. Real tokenization, instruction/context length,
shared account usage and abuse can change this. A planned average does not guarantee headroom.
Use account-level Free hard-stop plus a lower shared application quota, atomic reservations,
strict per-request token limits and immediate local fallback at exhaustion. No automatic retry,
larger paid model or alternate paid provider. These controls remain Phase 3.3 work.

## Gemini API Free Tier

[Additional terms](https://ai.google.dev/gemini-api/terms?hl=en) require API users to be 18+ and
restrict API clients directed at or likely to be accessed by under-18s. They also require Paid
Services when making clients available to users in the EEA, Switzerland or UK. A public VGU
site with possible minors and Germany/EU visitors therefore cannot assume Free Tier suitability.
This is a blocking provider-selection issue; do not solve it by enabling billing.

The same terms describe unpaid input/output use for product improvement and human review and
warn against submitting personal/confidential data; regional data-treatment exceptions do not
remove the separate Paid Services restriction for EU-facing clients. Paid data handling still
has safety/legal logging conditions. Public student questions can contain personal data even
when the knowledge base is public.

[Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) are model/project/tier dependent;
RPM, input TPM and RPD can independently reject requests, and daily request quotas reset at
midnight Pacific time. Active limits require account inspection and are not guaranteed capacity.
[Billing](https://ai.google.dev/gemini-api/docs/billing/) and
[pricing](https://ai.google.dev/gemini-api/docs/pricing) distinguish unpaid eligibility from paid
features. Do not activate billing, use paid grounding, buy credits or rely on a Cloud trial to
meet the zero-additional-cost requirement. No Gemini SDK/dependency or adapter is installed.

## Phase 3.2 exit checklist

1. Resolve Cloudflare age/audience/model-license and EU processing suitability; record the
   responsible reviewer's evidence. Gemini remains unsuitable under the current Free/public-EU
   assumptions unless official terms and audience scope change.
2. With separately authorized account inspection, verify a Free-only account, eligible allowlisted
   model and provider hard-stop; record no tokens or private account identifiers in evidence.
3. Prepare a balanced redacted EN/DE benchmark: grounded FAQ paraphrases, unknowns, contradictory
   sources, injection, personal-data requests, ambiguity, quota exhaustion and timeout errors.
4. Define acceptance thresholds and token/latency budgets before any inference. If compliance
   or zero-cost safeguards remain unresolved, benchmark retrieval locally and keep AI disabled.
5. Any later inference experiment requires verified safeguards and explicit authorization;
   Phase 3.2 research alone does not authorize billing, deployment or private-data tools.
