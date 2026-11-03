# CHATBOT-KB-001 — Phase 3.1 knowledge base and local prototype

**Assigned:** 2026-10-22 (Asia/Saigon), explicit owner request in pasted task.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.
**Baseline:** clean `main` at `f88c18d`.

Implement structured bilingual knowledge/FAQs, historical prompt audit, conservative retrieval,
provider-independent local backend service/CLI, focused tests and official provider research.
The external `systemPrompt.txt` is untrusted historical evidence and must remain unchanged.
No public route/UI, inference calls, new dependency, migration, private-data access, cloud setup,
push or deployment. Existing release/owner-action blockers remain independent.

Focused source: `apps/api/app/services/chatbot/`, `apps/api/tests/test_chatbot.py`, API package
data declaration. Inspect existing main/router/auth/rate-limit modules and frontend route,
registration, Matching and Event source only to establish boundaries and guide accuracy.
Documentation: `docs/project-knowledge/chatbot/`, affected knowledge entry points and current
task/control-plane/index/validation records. Acceptance follows all nine Phase 3.1 tasks in the
owner request; uncertain institutional claims must remain quarantined from retrieval.

Validation: bilingual FAQ/relevance/abstention, knowledge trust/schema, input/output/context bounds,
language ambiguity, injection/private-data isolation, disabled provider and failure fallback,
independent knowledge/provider replacement, no application route exposure, CLI/package smoke,
Ruff/mypy, relevant existing app tests and task/link coverage. Record actual runtime and limits.

## Verified outcome — 2026-10-22

Implemented the isolated `app/services/chatbot` pipeline and stdin/JSON CLI, packaged category
JSON, 17 bilingual FAQs (two official-source / fifteen code-confirmed) and nine excluded historical
summaries. FAQ-first retrieval returns source/status/date metadata or explicit uncertainty.
Conservative lexical EN/DE detection is independent of UI language. Typed provider contracts and
compact instructions are separate; provider injection cannot enable generation in this phase.
No public endpoint, UI, database dependency, private tool or new runtime package was added.

[Phase record](../../project-knowledge/chatbot/README.md),
[source audit](../../project-knowledge/chatbot/SOURCE_AUDIT.md) and
[provider assessment](../../project-knowledge/chatbot/PROVIDERS.md) contain architecture,
verification limits, FAQ coverage, zero-cost controls and the Phase 3.2–3.6 roadmap. Original
prompt bytes remain unchanged. Cafeteria/passport contradictions, old prices and other sensitive
or transient claims remain unavailable to authoritative retrieval. Official-page placeholders
and Buddy-page fetch failures are recorded rather than treated as verified procedure evidence.

Final checks on the existing local Python 3.14.0 environment:

- `python -m pytest tests/test_chatbot.py tests/test_app.py -q` with a workspace-local basetemp:
  **147 PASS** (145 new chatbot cases and two existing application smoke tests).
- `python -m ruff check app/services/chatbot tests/test_chatbot.py`: **PASS**.
- `python -m ruff format --check app/services/chatbot tests/test_chatbot.py`: **PASS**.
- `python -m mypy app/services/chatbot tests/test_chatbot.py`: **PASS**, nine checked files.
- `python -m build --wheel --no-isolation --outdir dist/chatbot-local`: **PASS**; extracted
  wheel contains all eight JSON files and independently runs the FAQ CLI away from source.
- Task index, changed-document/source paths, JSON source references, unchanged legacy archive
  and original-input hash, scope/secret review and `git diff --check`: **PASS**.

Initial verification caught a German inflection miss and fixed it. Default sandbox temp writes
failed; using workspace-local temporary directories resolved packaging/fixture writes. The
Windows sandbox also stalled asyncio's local socket-pair initialization (captured stack trace);
the final isolated tests passed outside that sandbox without external service calls. Docker
was unavailable; no Python 3.12/container or full backend/frontend regression is claimed.
Existing UI/domain source is unchanged, so completed gates were not repeated.

No inference, paid resource, push, deployment, private-data access or Production operation.
Local `main` commit only; its resulting hash is reported in the completion response. Task is clear.
Next: Phase 3.2 Cloudflare age/EU/license/free-account review and redacted bilingual benchmark
design. Keep generation disabled until the documented safeguards and separate authorization exist.
