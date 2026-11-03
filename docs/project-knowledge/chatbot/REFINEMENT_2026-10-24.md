# Historical references and interaction refinement

2026-10-24 (Asia/Saigon), [CHATBOT-REFINE-001](../../implementation/tasks/CHATBOT-REFINE-001.md).
Baseline: clean local `main` at `ddb0220883a16901b064c4b9bf7442255bf636d4`.
Local acceptance only; no push/deployment. This record supersedes only the earlier corpus,
response-contract and transition descriptions. Completed Phase 3.1–3.4 records stay historical.

## Root cause

| Check                | D9 food                                                                            | Laundry                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Original source      | `systemPrompt.txt`, lines 235–248: restaurants outside D9 Gate; nearby street food | Lines 420–421: EVA, laundry next to automobile repair, food place on D9 Street under Laundry |
| Migration            | No food entry in any of the original eight files                                   | No laundry entry in any of the original eight files                                          |
| Historical metadata  | Not one of the nine excluded summaries                                             | Not one of the nine excluded summaries                                                       |
| Eligibility          | Retriever constructed its candidate set from `entry.authoritative` only            | Same                                                                                         |
| Language / relevance | EN detected correctly; zero eligible hits; no relevant candidate reaches scoring   | Same                                                                                         |
| Construction / API   | `insufficient`, `supported=false`, no sources, established fallback                | Same                                                                                         |
| Frontend             | Correctly rendered the API miss; no lost answer or schema rejection                | Same                                                                                         |

Both failures were reproduced before edits using the real service and public projection. The
loss was incomplete migration plus the verified-only policy, not a global threshold defect.
The original document's chatbot instructions were treated as data, never agent instructions.
See [preserved exact excerpts and SHA-256](HISTORICAL_SOURCE_2026-10-24.md). The owner explicitly
recontracted these two low-risk topics; the original file remains unchanged.

## Knowledge and public response contract

The original eight JSON files remain byte-identical: **17 verified FAQs and nine exclusions**.
A ninth file, [historical-references.json](../../../apps/api/app/services/chatbot/data/historical-references.json),
adds only `legacy-d9-food` and `legacy-laundry`. Both are still `unverified`, with
`verified_on=null`. Explicit eligibility requires those IDs, student-life category, unverified
status, no verification date and the exact original `historical:` source/line identifier.

Verified retrieval takes precedence. Ambiguous verified results clarify instead of falling
through to historical material. Historical matching requires equality of the complete normalized
query/curated alias; it does not use fuzzy overlap. Explicit EN/DE aliases cover the demonstrated
questions and close food/restaurant/eating and laundry/washing paraphrases. Existing verified
thresholds (coverage 0.7, precision 0.5, ambiguity gap 0.12) remain unchanged. Digits survive
normalization so D8 cannot become D9; German `gibt` is now a language marker after a failing test.

Answers are fixed EN paraphrases/DE translations of the preserved excerpts, with a current-status
qualification in every historical answer. No new address, business, price, operating hour,
turnaround, current availability, medical/immigration/legal/financial claim was invented or
imported. EVA is not assigned a fabricated street address. Unrelated summaries remain excluded.
Unknown modifiers (prices, current opening, allergy, medical laundry, visa) abstain. Removing a
supporting entry fails closed. Corrupt packaged data retains the existing unavailable behavior.
Historical references remain excluded from provider context; provider abstraction is unchanged.

Public success extends the existing DTO with `status=historical_reference`; each historical source
has `verification_status=historical_reference`, `verified_on=null`, stable entry ID and title
`Historical student guide (systemPrompt.txt)`. `supported=true` means supported by a named source,
**not current verification**. Mixed verified/historical answers use historical status and preserve
individual citation statuses. No local path, full prompt, fabricated public link or verification
date is exposed. The frontend validates status/date/title/ID consistency and displays a localized
historical badge plus a source label saying it is not currently verified. Existing verified
answers/citations are unchanged. API limits, guards, auth/CSRF/cookie boundaries are unchanged.
Deploy frontend/API together when separately authorized: the old client rejects the new status.

Ordinary misses no longer instruct a user who asked one question to ask one question. Multiple
unanswered parts receive EN/DE separate-question guidance; ambiguous candidates receive a topic
clarification. Language choice and service-unavailable messages stay separate. The offline test
scorer/mock harness now recognize the revised multi-part fallback; the 60-case dataset and prior
benchmark reports were not rewritten or rerun as a new provider benchmark.

## Interaction

The lazy widget uses closed/open/closing states. Enter is a 220ms ease-out opacity/10px translation/
small scale keyframe; exit is a faster 180ms counterpart. The panel stays mounted through exit.
Native `animationend` completes teardown, with a computed-duration +50ms fallback for a lost event.
Reduced-motion CSS disables keyframes and icon transitions; zero duration tears down next task.
Rapid reopening cleans up the prior exit listener/timer and cancels pending focus restoration.
Closing before the lazy chunk mounts removes only the loading fallback.

Close still aborts the active request immediately and keeps completed in-memory turns. Exiting
content becomes inert/aria-hidden, its live log turns off and pointer events stop immediately.
Mobile isolation/scroll lock releases before focus returns to the launcher. Only a real close
restores focus; initially mounting a closed widget never steals focus. App focus calls use
`preventScroll`. Enter/Escape/mobile focus loop and source links keep their existing semantics.
The expanded launcher is hidden on mobile, leaving one accessible header close action.

Actual 320px focus/citation testing found outer `overflow:hidden` could scroll internally and
move the header offscreen. `overflow:clip` makes the panel non-scrollable; only the message log
scrolls. Final header top=0, composer bottom=viewport height, outer scrollTop=0 at 320/390px.
VisualViewport resizing/safe areas are retained. No animation library or dependency was added.

## Validation

- Backend focused: **357 PASS** (knowledge, historical, evaluation and API files).
- Full non-live backend: **1774 PASS**, 63.27s, existing AnyIO/Starlette deprecation warning.
- Final frontend chatbot + shared transport: **95 PASS / 4 files**.
- Existing Landing/slideshow/slider/navbar/User layouts: **82 PASS / 11 files**.
- Ruff, changed-file Python format, strict mypy **128 source files**, TypeScript, affected ESLint,
  Prettier and flag-ON/OFF production builds PASS. Existing large-entry advisory remains.
- Wheel build/extraction PASS: all **nine packaged JSON files** byte-identical to source;
  extracted service returns EN/DE historical DTOs. No new package dependency.
- Real loopback API: **7** EN/DE/status/citation/no-store/fallback checks PASS.
- Real Brave -> Vite 5182 -> guarded Uvicorn 8012 -> packaged retrieval -> UI: both original
  questions, DE equivalents, verified registration, unsupported weather and excluded passport PASS.
  Historical labels/IDs and no false verification dates; verified answer unchanged.
- Browser inspection at **1440x900, 768x1025, 390x844, 320x800**, plus **390x400** short viewport.
  One mobile close control, modal isolation/body lock, input focus, keyboard focus wrapping,
  Escape/restoration, message-only scrolling and no chatbot horizontal overflow checked.
- Actual reduced-motion emulation: `animation:none`, duration `0s`, functional close/reopen.
  Actual 4x CPU throttling: rapid launcher double-click/reopen and inert exit/unmount checked;
  emulation restored. This is a functional check, not an FPS measurement or physical-device test.

Initial failures identified the German marker, expected revised fallback text, Unicode fixture
encoding and incomplete style/animation event doubles; fixed. An initial sandboxed Python run was
stopped when Windows socket restrictions stalled it; all reported API results are the completed
unsandboxed loopback/fixture runs. Occupied 8010/5180 services were left untouched. Browser control
had intermittent capture/resize timing and one slow emulation call; final settled DOM and actual
screenshots were inspected. Hot-update resets were checked with a reload. Ignored screenshots:
`.local/refine-visuals/` (mobile and narrow final views). No physical keyboard, hardware screen
reader or real account acceptance claimed. The existing DE Landing 329px document at 320px remains;
chat panel is 320px. Previous Phase 3.4 OFF-build evidence already isolates that page overflow.

## Reproduce locally (PowerShell)

From `apps/api`:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_chatbot_historical.py tests/test_chatbot.py tests/test_chatbot_evaluation.py tests/test_chatbot_api.py -q
.venv/Scripts/python.exe -m pytest tests -q --ignore-glob=tests/*live.py
.venv/Scripts/python.exe -m ruff check app tests
.venv/Scripts/python.exe -m mypy app tests/test_chatbot_historical.py tests/test_chatbot_api.py tests/test_chatbot.py tests/test_chatbot_evaluation.py
.venv/Scripts/python.exe -m build --wheel --no-isolation --outdir dist/refine
$env:APP_ENV='local'
$env:RATE_LIMIT_STORAGE_URI='memory://'
$env:CHATBOT_API_ENABLED='true'
$env:CHATBOT_AI_ENABLED='false'
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8012 --no-proxy-headers --no-access-log
```

From `apps/web` (workspace-local TEMP/TMP used for Vitest worker stability):

```powershell
New-Item -ItemType Directory -Force .local/refine-test-tmp | Out-Null
$env:TEMP=(Resolve-Path .local/refine-test-tmp).Path
$env:TMP=$env:TEMP
node_modules/.bin/vitest.cmd run src/features/chatbot src/lib/api.test.ts --maxWorkers=1 --no-file-parallelism --no-cache --reporter=dot
node_modules/.bin/vitest.cmd run src/components/landing src/pages/public/landing-page.test.tsx src/components/layout/navbar.test.tsx src/components/layout/user-layout.test.tsx src/components/layout/user-layout-integration.test.tsx --maxWorkers=1 --no-file-parallelism --no-cache --reporter=dot
npm.cmd run typecheck
node_modules/.bin/eslint.cmd src/features/chatbot
node_modules/.bin/prettier.cmd --check src/features/chatbot src/locales/en/common.json src/locales/de/common.json
$env:VITE_API_URL='/api'
$env:VITE_CHATBOT_ENABLED='true'
npm.cmd run build -- --outDir dist/refine-on --manifest
$env:VITE_CHATBOT_ENABLED='false'
npm.cmd run build -- --outDir dist/refine-off --manifest
$env:VITE_CHATBOT_ENABLED='true'
$env:LOCAL_API_PROXY_TARGET='http://127.0.0.1:8012'
npm.cmd run dev -- --host 127.0.0.1 --port 5182 --strictPort
```

Acceptance used a disposable guarded API wrapper with synthetic local signing configuration;
not real accounts. The wrapper rejects provider, private database and non-loopback calls.
Windows process termination did not persist its shutdown counters; no numerical zero-attempt
metric is claimed. Disabled providers and guarded transport prevent paid inference/egress.
Default feature flags remain OFF in source. Temporary owned processes are stopped after acceptance.

## Phase 3.5 boundary

Ready for a separately assigned release-readiness evaluation, not release approval. Historical
business information remains unverified and intentionally narrow. Provider Free/payment-free,
age/EU/privacy/license eligibility is unresolved; Gemini/Cloudflare remain disabled. Deployed
proxy trust/access-log retention, process-local quota multiplication/restarts, operational release/
recovery gates and real-device/SR acceptance remain separate. No database, account, cloud,
Production configuration or billing action; no persistent chat history; zero additional operating
cost. Do not push or deploy from this task.
