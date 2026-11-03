# Phase 3.5 — executed local commands and evidence

2026-11-01. See [report/gates](PHASE_3_5.md). Isolated detached checkout from main 9ec; primary dirty
work was not used as the implementation tree. No Production chatbot requests, push or deployment.

PowerShell from repository root created `.local/phase35/venv` with installed Python 3.12 and reused
already installed packages through a local `.pth`; no dependency download/upgrade. The isolated
frontend node_modules junction reused a cache checked against all 438 installed lock entries.
The original existing environments were not installed into or modified.

From `apps/api`:

```powershell
../../.local/phase35/venv/Scripts/python.exe -m pytest tests/test_chatbot_api.py tests/test_chatbot_source.py tests/test_rate_limits.py tests/test_observability.py -q
../../.local/phase35/venv/Scripts/python.exe -m pytest tests -q --ignore-glob=tests/*live.py
../../.local/phase35/venv/Scripts/python.exe -m pytest tests/test_chatbot.py -q -k cli
../../.local/phase35/venv/Scripts/python.exe -m ruff check app tests/test_chatbot.py tests/test_chatbot_api.py
../../.local/phase35/venv/Scripts/python.exe -m mypy app tests/test_chatbot.py tests/test_chatbot_api.py
../../.local/phase35/venv/Scripts/python.exe -m build --wheel --no-isolation --outdir dist/phase35
```

Focused203 PASS; final full 1851 PASS/79.89s/one existing deprecation; final CLI 7 PASS. Subsets and
pre-fix checkpoints are not added together. Ruff format checked touched Python files. mypy 129 files.
Exact executed runs also supplied distinct workspace-local `--basetemp` and log redirection under
`apps/api/.local/phase35/`; the commands above omit only these output-path arguments. Runtime
pin comparison37/37 and pip check PASS. Build/extracted wheel checks PASS, including Unicode from
an unrelated cwd. A Python wheel is verified; a current Linux Docker image was NOT built or run.

From `apps/web`, TEMP/TMP set to its `.local/phase35`:

```powershell
node_modules/.bin/vitest.cmd run src/features/chatbot src/lib/api.test.ts --maxWorkers=1 --no-file-parallelism --no-cache --reporter=dot
npm.cmd run typecheck
node_modules/.bin/eslint.cmd src/features/chatbot
node_modules/.bin/prettier.cmd --check src/features/chatbot
$env:VITE_API_URL='http://127.0.0.1:8025/api'
$env:VITE_CHATBOT_ENABLED='true'
npm.cmd run build -- --outDir dist/phase35-on --manifest
$env:VITE_CHATBOT_ENABLED='false'
npm.cmd run build -- --outDir dist/phase35-off --manifest
node_modules/.bin/vite.cmd preview --host 127.0.0.1 --port 5195 --strictPort --outDir dist/phase35-on
node_modules/.bin/vite.cmd preview --host 127.0.0.1 --port 5196 --strictPort --outDir dist/phase35-off
```

101 PASS/4 files/27.87s; static/ON-OFF builds PASS, existing chunk-size advisory. No full frontend
suite is claimed. Built UI was exercised with real loopback HTTP, not mocked browser responses.

Disposable local-only harnesses are retained under ignored `.local/phase35/` for this workspace:

```powershell
.local/phase35/venv/Scripts/python.exe .local/phase35/package.py
.local/phase35/venv/Scripts/python.exe -u .local/phase35/server.py true
.local/phase35/venv/Scripts/python.exe .local/phase35/http_load.py
.local/phase35/venv/Scripts/python.exe -u .local/phase35/server.py false
.local/phase35/venv/Scripts/python.exe .local/phase35/multiprocess.py
```

They extract the wheel, enforce loopback-only connections/DNS, reject provider/private DB access,
generate ephemeral local signing fixtures internally, bind only owned8025/8026, and use synthetic
inputs. No key values appear in arguments/logs/evidence. They are local evidence helpers, not
application code, deployment commands or a tracked reusable load-testing tool. Do not point them
at cloud services. Standard committed pytest checks reproduce the underlying security contracts.
Two API processes were automatically stopped by the multiprocess driver; previews and remaining
owned API processes were stopped manually after browser acceptance. Existing user services untouched.

Local evidence: package.json/load.json/multiprocess.json/guards*.json and server logs under that
ignored folder; test/static/build logs under each app's `.local/phase35/`. Browser screenshots and
metrics are retained in the task's local visualization output. No synthetic facts were inserted in
tracked knowledge. Initial load-harness header-case/language expectations were corrected, the
CLI test was rerun from its documented API cwd, and a duplicate test import/mypy export annotation
were corrected. Failed intermediate runs are not PASS evidence.

Unavailable/unclaimed: Docker daemon/Linux container execution, exact integrated candidate CI,
actual Render proxy/edge logging/env/worker acceptance, Production chat smoke, real authenticated
accounts, physical mobile keyboard, hardware screen reader and final combined current-UI artifact.

Preservation check: all 256 pre-existing dirty/untracked file content hashes and primary HEAD/main
match the initial fingerprint; its index remains empty. At closeout the architecture-study folder
is excluded by `.git/info/exclude` and therefore no longer listed as untracked. Its files remain
byte-identical; the exclusion rule was not changed or removed by this task.
