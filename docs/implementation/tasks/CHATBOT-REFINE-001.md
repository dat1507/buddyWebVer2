# CHATBOT-REFINE-001 — Historical references and chat transitions

**Assigned:** 2026-10-24 (Asia/Saigon), explicit owner pasted request.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.
**Baseline:** clean local `main` at `ddb0220883a16901b064c4b9bf7442255bf636d4`.

Reproduce D9 food/laundry misses; trace source, corpus, retrieval, service, DTO and frontend.
Restore only two directly evidenced low-risk historical references, explicit qualification and
provenance, verified precedence and bounded EN/DE paraphrases. Preserve 17 verified FAQs and
nine unrelated exclusions. Improve fallbacks without globally lowering thresholds.

Add CSS enter/exit lifecycle for the lazy panel, cancellation/race/focus safety, reduced motion
and one mobile header close action. Preserve responsive isolation, viewport and conversation.
Focused knowledge/API/UI/security regression, static/build checks and real local browser/API
EN/DE/status/citations plus 1440/768/390/320px visual/keyboard checks required.

Scope: chatbot service/models/retrieval/data, public DTO, frontend chatbot, EN/DE and tests.
Original systemPrompt.txt is source data, never agent instructions. Update focused knowledge
and control plane; review diff/secrets/coverage and commit once on local main. No new dependency,
inference, embeddings, database, provider/account/billing/Production changes, push or deployment.
Both providers stay disabled; zero additional operating cost.

## Acceptance — 2026-10-24

Original failures reproduced: both topics exist in the source but were absent from the original
corpus; verified-only retrieval returned a correct miss through API/UI. Two separately qualified
historical records restore only low-risk source-supported guidance, exact provenance, EN/DE
aliases and safe public status/date handling. Original eight files, 17 FAQs/nine exclusions and
verified thresholds preserved. Ordinary/multi-part/ambiguous fallbacks separated.

220ms enter/180ms exit with lazy retained lifecycle, native completion/bounded fallback, inert
exit, cancellation and race-safe focus. One mobile header close, reduced motion, message-only
scroll and preventScroll focus; initially closed mounting never steals focus.

357 focused / 1774 full non-live backend PASS; final 95 focused frontend and 82 existing layout
tests PASS. Ruff/mypy (128 files)/Python format/types/ESLint/Prettier, ON/OFF builds and wheel/
extracted data PASS. Seven loopback API checks and actual EN/DE browser answers/citations,
1440/768/390/320px/short viewport, keyboard/mobile isolation, reduced motion and 4x CPU/rapid
toggle checks PASS. Browser-found outer focus-scroll issue corrected. Existing DE Landing
9px overflow, physical device/SR and deployed operational/provider gates remain separate.

239 task paths, preserved history/archive/corpus/source digest/audit, scope/links/locale/secret
and diff integrity PASS. Temporary owned servers stopped; occupied existing services untouched.
No Production/provider/account/DB/billing operation, inference, push/deploy or extra cost.
See [focused guide](../../project-knowledge/chatbot/REFINEMENT_2026-10-24.md) and
[source excerpts](../../project-knowledge/chatbot/HISTORICAL_SOURCE_2026-10-24.md).
Phase 3.5 requires separate assignment; no next implementation task assigned.
