# Canonical source and intent-aware retrieval

2026-10-24 (Asia/Saigon), [CHATBOT-SOURCE-001](../../implementation/tasks/CHATBOT-SOURCE-001.md).
Baseline: clean `main`, `df7d3ae6ec69a3599e7fe70623f551fbbbb902b6`. Local only; no push/deployment.
This supersedes the two-entry-only runtime source policy, not the completed historical acceptance records.

## Source and processing

The old API cached a service constructed from nine JSON files. It never loaded the external original
`systemPrompt.txt`; manually prepared FAQ/historical aliases were its only source. The canonical file is
now [sources/systemPrompt.txt](../../../apps/api/app/services/chatbot/sources/systemPrompt.txt), imported
byte-for-byte from the owner-supplied original: **22129 bytes / 431 lines**, SHA-256
`0fe1c16900d47c2c57e50d56cdc3ee4b2bd66dc9d6b2ccd2366256162519f0a8`. A scoped `.gitattributes` preserves
these bytes, including original CRLF/trailing whitespace, across checkouts. The source-only whitespace
exception avoids normalizing the historical document during Git checks. No historical text was edited, scraped, corrected or supplemented by AI.

[SourceIndex](../../../apps/api/app/services/chatbot/owner_source.py) reads at most 256000 bytes,
validates UTF-8/controls/credential-like content, detects headings, sentences and table rows, and indexes
all source passages. The imported source yields **174 passages**; all nonblank source lines are covered.
Factual lists, contacts, locations and prices are preserved verbatim. Source instructions remain in the
canonical file/history but are excluded as answer evidence and never executed. No corpus generator,
vector store, database, remote synchronization, dependency or provider call was added.

Bounded reads plus SHA-256 detect changes even if an editor preserves size/mtime. Unchanged bytes reuse
the immutable parsed/tokenized snapshot and cached document frequencies. A lock and stable before/after
file stats protect construction; only a complete validated snapshot is published. At most two read
attempts handle a changing file. Invalid/unreadable/deleted source clears eligibility immediately; the
old snapshot is not served. Same invalid bytes do not reparse. A corrected save recovers automatically.
There is one snapshot per service, shared by the cached API service; the CLI uses the same default path.
Verified FAQ requests bypass source I/O/parsing, including cold starts and invalid guide edits.

All **nine existing JSON files / 17 verified FAQs / two historical references / nine historical exclusion
records and their metadata remain unchanged**. They retain traceability and the isolated explicit-entry
prototype/evaluation contract. Default API/CLI guide facts come only from the canonical index; the two
manually copied guide answers are excluded from the runtime candidate set. Deleting canonical food/
laundry content cannot resurrect their old JSON copies. Code/official FAQs remain supplementary.

## Selection and responses

The original verified FAQ retriever/thresholds remain intact. [Intent vocabulary](../../../apps/api/app/services/chatbot/intents.py)
adds EN/DE topics for food, laundry, transport, housing, library, sports, Buddy Program, registration,
login, verification, matching, invitations, chat, events, facilities, groceries, internet, contacts,
health, arrival and banking. It contains search terms/IDs, no factual answers. Actual available evidence
and constraints gate selection. New source headings/names are also searchable without defining a new
intent. [Owner retrieval](../../../apps/api/app/services/chatbot/owner_retrieval.py) reuses existing token/
stop-word behavior, with spelling/umlaut variants, identifier preservation, phrase normalization and
cached lexical document-frequency scoring. Unmatched places/numbers/constraints are not discarded.
Generic lexical coverage/ambiguity constants are 0.8/0.15; no verified threshold was lowered.

Clear intent plus evidence answers directly. Short incomplete queries receive a conditional
interpretation plus quoted evidence; competing topics clarify. High intent without evidence abstains.
Shared `Restaurant`/`Taxi` or a source-only short proper name defaults deterministically to English;
`Essen`, `Wäscherei` and unique DE vocabulary select German. Explicit EN/DE sentence detection retains
priority. Balanced/unrecognized language still requests EN/DE rather than guessing arbitrary languages.

Source facts are quoted, not generated. German surrounding text is localized; English source material
is explicitly **untranslated**. This is a deliberate limitation, not full automated translation.
Names, amounts, dates and addresses are unchanged. No fabricated factual addition or factual synonym
mapping exists. Long passages remain cited but are not truncated into misleading partial sentences.
Multi-part answers deduplicate evidence and retain answer/citation bounds, marking unanswered parts.

- Verified FAQs retain `answer`, actual verification dates and existing sources.
- Canonical evidence uses `owner_provided`, null verification date and source hash/lines/section.
- Conflicts use `conflicted` and cite the actual conflicting passages, without silently choosing one.
- Ambiguous intent uses `clarification` without falsely claiming source support; misses/errors remain separate.

Known passport month counts, cafeteria dinner assertions and dorm-room VND ranges are compared from
source text; explicit conflict markers and differing single-valued fields also flag conflicts. This is
not universal contradiction detection. Medical/legal/insurance and similar source passages require
explicit reference intent to quote. Normal high-stakes/current-fee questions abstain from current
advice. Time-sensitive references carry additional qualification; current status is never inferred.
Owner-provided content can never acquire `verified` status merely by being present in the file.

The POST request, stateless transport, quotas/body/workers/deadlines/output bounds and auth/CSRF/cookie
exceptions are unchanged. Source selection paths are constructor-only, never client input. Public
provenance contains only `systemPrompt.txt`, hash, line range and section, never a filesystem path.
The frontend validates these states/metadata, adds localized labels and collapsed citation details,
and retains the existing animation/mobile/focus/cancellation implementation. Old verified payloads
retain their shape; new states require a coordinated frontend/API release, not an unpaired rollout.

## Validation

Focused tests ran before broader regression. Final backend/frontend results and commands are recorded
in [validation](../../implementation/validation.md) and the task extract. Existing 60-case dataset/
provider benchmark reports remain historical; only their regression tests were run. No live inference.

Real Brave -> Vite **5184** -> guarded Uvicorn **8014** -> same cached source service -> UI verified all
11 required scenarios: D9 food, where/eat/reversed/eat keyword, DE where/Essen, laundry/keyword/DE keyword,
verified registration and unsupported Mars weather. Clear questions answered; short terms were conditional;
German wrapper/untranslated quote explicit; registration unchanged; unsupported query abstained. Citation
example: original laundry lines **420–421**, source prefix **0fe1c16900d4**.

A temporary byte-identical source copy drove the same cached API process (not the tracked canonical file):

| Change                                     | Actual browser result                                          |
| ------------------------------------------ | -------------------------------------------------------------- |
| Add `Fixture Observatory` at lines 433–434 | Owner-provided North-roof quote, hash prefix `924a4ec9d9eb`    |
| Edit North to South                        | South quote replaces old answer, hash prefix `88ccd97f7684`    |
| Delete temporary section                   | Insufficient information, no stale quote/source                |
| Insert NUL invalid source                  | Safe unavailable UI/503; no old answer                         |
| Restore original bytes                     | Owner-provided food answer available again without API restart |

Older chat bubbles remain a record of previous requests, not a stale retrieval index. Locale hot updates
reset the in-memory widget as expected; no persistent history was added. All fixture facts were removed;
the tracked source was never changed for tests. API later restarted only to load final wording changes.
No real account/DB/provider/external access: disposable guard counters stayed zero. Only owned 5184/8014
processes are stopped at completion; existing services remain untouched.

DOM checks at **1440x900** and **390x844** retain panel bounds, mobile modal isolation, hidden expanded
launcher, no panel horizontal overflow and outer scrollTop=0. Actual desktop/mobile screenshots
inspected. Initial desktop capture timeouts were resolved after viewport and close/open state changes.
Physical keyboard/hardware SR and deployed rollout acceptance remain separate. Existing DE Landing
320px document overflow is prior evidence and not reworked here. No animation/CSS refactor was made.

Reproduce from `apps/api`:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_chatbot_source.py tests/test_chatbot_api.py -q
.venv/Scripts/python.exe -m pytest tests -q --ignore-glob=tests/*live.py
.venv/Scripts/python.exe -m ruff check app tests
.venv/Scripts/python.exe -m mypy app tests/test_chatbot_source.py tests/test_chatbot_api.py tests/test_chatbot.py tests/test_chatbot_historical.py tests/test_chatbot_evaluation.py
.venv/Scripts/python.exe -m build --wheel --no-isolation --outdir dist/source
$env:APP_ENV='local'
$env:RATE_LIMIT_STORAGE_URI='memory://'
$env:CHATBOT_API_ENABLED='true'
$env:CHATBOT_AI_ENABLED='false'
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8014 --no-proxy-headers --no-access-log
```

From `apps/web` (workspace-local TEMP/TMP used for Windows Vitest stability):

```powershell
New-Item -ItemType Directory -Force .local/source-test-tmp | Out-Null
$env:TEMP=(Resolve-Path .local/source-test-tmp).Path
$env:TMP=$env:TEMP
node_modules/.bin/vitest.cmd run src/features/chatbot src/lib/api.test.ts --maxWorkers=1 --no-file-parallelism --no-cache --reporter=dot
npm.cmd run typecheck
node_modules/.bin/eslint.cmd src/features/chatbot
node_modules/.bin/prettier.cmd --check src/features/chatbot src/locales/en/common.json src/locales/de/common.json
$env:VITE_API_URL='/api'
$env:VITE_CHATBOT_ENABLED='true'
npm.cmd run build -- --outDir dist/source-on --manifest
$env:VITE_CHATBOT_ENABLED='false'
npm.cmd run build -- --outDir dist/source-off --manifest
$env:VITE_CHATBOT_ENABLED='true'
$env:LOCAL_API_PROXY_TARGET='http://127.0.0.1:8014'
npm.cmd run dev -- --host 127.0.0.1 --port 5184 --strictPort
```

See the practical [owner update guide](OWNER_GUIDE.md). Invalid fixtures, same-metadata edits, additions/
edits/deletions, atomic concurrent replacement, unchanged cache, source instruction exclusion, all source
line coverage, exact quotes, verified precedence and safe source/status validation are tested. Initial
oversized pytest parameter IDs, old status/language assertions, deadline/paraphrase/price guards and test
annotations were corrected. Final diff review also fixed oversized conflict quotations to retain
conflicted status even when only a cited reference fits; its regression test passes. Failed
intermediate runs are not counted as acceptance.

Phase 3.5 remains separately assigned: coordinated release/proxy/logging/process-local limiter/recovery
acceptance, provider eligibility and real-device/SR gates stay open. Both providers and API/frontend feature
flags default OFF. No dependency, cloud service, account, database, billing, push/deploy or additional
operating expense. Local file edits reach Production only through a separately authorized deployment.
