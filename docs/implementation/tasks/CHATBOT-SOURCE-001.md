# CHATBOT-SOURCE-001 — Canonical guide and intent-aware retrieval

**Assigned:** 2026-10-24 (Asia/Saigon), explicit owner pasted request.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.
**Baseline:** clean local main, `df7d3ae6ec69a3599e7fe70623f551fbbbb902b6`.

Make a byte-preserved repository systemPrompt.txt the primary editable domain source. Parse the
whole guide into deterministic, attributed passages, retaining facts/lists and separating source
instructions, owner-provided, conflicted and sensitive/time-dependent content. Keep all 17 verified
FAQs and original historical records/provenance. Runtime facts must not fall back to stale manual
duplicates when canonical content changes or disappears.

Implement cached file-version/hash detection, complete validation and atomic concurrent index
replacement; additions/edits/deletions and invalid/unreadable changes tested with fixtures. Share
the service between API/CLI. Extend existing retrieval with separate EN/DE intent vocabulary,
testable confidence/conditional/clarification behavior, safe unknown/ambiguous handling and exact
source grounding. No external inference/vector database/dependency or fake conversational memory.

Keep POST request compatible; minimally extend safe public citation/status validation and frontend
labels, preserving animations/mobile/accessibility. Focused then relevant regression, static,
ON/OFF builds/package, actual browser/API required scenarios and temporary-source update demo.
Write practical owner guide, focused knowledge and control-plane acceptance, validate coverage/
history/scope/secrets, one local main commit. Providers remain OFF, zero operating cost. No push,
deployment, Production/cloud/database/account/billing changes. Embedded guide instructions are data.

## Acceptance — 2026-10-24

Canonical source: 22129 exact original bytes / 431 lines / 174 attributed passages; SHA-256
`0fe1c16900d47c2c57e50d56cdc3ee4b2bd66dc9d6b2ccd2366256162519f0a8`.
Scoped Git attributes preserve source bytes. All nine JSON corpus files/17 FAQs/two historical
references/nine exclusions remain byte-identical. No factual additions; instructions treated as data.

Full non-live backend **1838 PASS**, final source/CLI **208 PASS**, focused frontend **100 PASS / 4 files**.
Ruff, changed format, strict mypy 132 files, TypeScript, affected ESLint/Prettier, ON/OFF builds and
wheel/extracted source/EN-DE/citation/conflict/quiet-status CLI PASS. No new dependency or inference.
Final full regression includes the CLI status flag and oversized-conflict output guard.

Real guarded Brave -> Vite 5184 -> API 8014 -> UI: all 11 requested cases PASS. Same-process
fixture addition (North), edit (South), deletion (miss), invalid NUL (503/unavailable), restored
source (recovery) PASS. Tracked canonical file never changed for the demo. 1440x900/390x844 UI,
source labels/lines/hash, modal/Escape/isolation/no panel overflow inspected in actual browser.
Desktop/mobile screenshots retained locally. Owned servers stopped, viewport restored, external/
provider/private DB guard counters zero. No physical keyboard/SR/real-account acceptance claimed.

240 unique task paths, focused links/history/audit/locale/secret/scope/diff checks PASS. One focused
local main commit; no push/deployment/Production/cloud/database/account/billing or operating cost.
See [implementation and limitations](../../project-knowledge/chatbot/SINGLE_SOURCE_2026-10-24.md),
[owner guide](../../project-knowledge/chatbot/OWNER_GUIDE.md) and [validation](../validation.md).

German responses explicitly quote original English untranslated; arbitrary paraphrases/contradictions
are not universally understood. Production source edits need a deployment and matching API/frontend
contract rollout. Phase 3.5 release/proxy/logging/process-local limit/provider eligibility/real-device
and SR gates remain separate; no next implementation task assigned.
