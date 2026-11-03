# Phase3.5.1 — executed command evidence

2026-11-03. [Results and limits](PHASE_3_5_1.md). Local only; no push/deploy.
Run from the isolated integration worktree unless a working directory is stated. All generated
artifacts/logs/harnesses are ignored under `.local`, dist or node_modules; none are committed.

| Area | Executed command / result |
| --- | --- |
| Safe remote refresh | `git fetch --no-tags --no-recurse-submodules origin refs/heads/main:refs/remotes/origin/main`; initial origin/main5a; later independently verified current remote/Productionc64 |
| Preserve prior source | New `codex/chatbot-phase35-preserved` ref at full a1aa; managed clean integration worktree/branch from full5a, later normally fast-forwarded to currentc64 |
| Baseline advance | Retained exact task-only safety stash; fast-forward to c64; apply by hash; resolve task-index count by retaining all248 paths; no stash drop |
| Git audits | status/worktree/list/for-each-ref, merge-base, left-right ancestry, targeted blob/diff comparisons; original hashes/status/index/heads checked |
| Isolated Python | `py -3.12 -m venv --without-pip .local/phase351/venv`; reuse read-only cached packages, install cached Pillow13 and current wheel only into new env |
| Backend focus (apps/api) | `../../.local/phase351/venv/Scripts/python.exe -m pytest tests/test_chatbot.py tests/test_chatbot_api.py tests/test_chatbot_evaluation.py tests/test_chatbot_historical.py tests/test_chatbot_source.py tests/test_image_storage_security.py tests/test_rate_limits.py tests/test_observability.py -q --basetemp=.local/phase351/focused`;494 PASS |
| Backend static (apps/api) | Isolated Python `-m ruff check .`, `-m mypy app alembic tests`; PASS/318 files |
| Frontend install (apps/web) | `npm ci --offline --ignore-scripts --no-audit --fund=false`;436 packages, approved lock unchanged |
| Frontend focus | `vitest run src/features/chatbot src/lib/api.test.ts --maxWorkers=1 --no-file-parallelism --no-cache --reporter=dot`;101 PASS |
| Frontend full | `vitest run --maxWorkers=1 --no-file-parallelism --no-cache --reporter=dot`;920 PASS/91 files,633.75s on finalc64 |
| Frontend static | `npm run typecheck`, `npm run lint`, `npm run format:check`; final all PASS |
| Frontend builds | `npm run build -- --outDir dist/integration-off --manifest`, then integration-on; VITE_CHATBOT_ENABLED=false/true and VITE_API_URL=http://127.0.0.1:8035/api; PASS |
| Wheel/integrity | Isolated Python `-m build --wheel --no-isolation --outdir dist/phase351`; install current wheel into new env, `pip check`; PASS |
| Runtime audits | `npm audit --omit=dev --json`;0. Isolated Python `-m pip_audit --strict -r requirements.lock --format json`;36/0 skips/0 findings |
| Production Dockerfile | `docker build --pull=false --progress=plain -t buddyweb-chatbot-integration:20261103 apps/api`; PASS |
| Artifact probe | `docker run --rm --network none --read-only --tmpfs /tmp:rw,size=64m --workdir /tmp --interactive --entrypoint python buddyweb-chatbot-integration:20261103 -`; inline probe checks installed pins,uid,Pillow,exact source/module/JSON hashes, unrelated-cwd CLI, flags,seven queries and socket/provider guards |
| Actual HTTP fixture | Task-owned read-only non-root API container, internal network,1CPU/512MiB/64PIDs/cap-dropALL/no-new-privileges, tmpfs; byte-only relay publishes127.0.0.1:8035; defaultOFF then ON, noAI/envcredentials/DB |
| Synthetic HTTP check | Ignored `.local/phase351/http_load.py`;38 bounded chat requests, health/auth, CORS/spoof/limits, no-store/Retry-After, Docker stats; PASS |
| Browser | Built ON/OFF previews5197/5198; real local API response/citation, initial5a English4width bounds/Escape/focus; tool stopped before German/screenshot completion; finalc64 browser acceptance unverified |
| Cleanup | Task helper verifies labels/empty network before owned container/network removal; terminate only two owned preview processes |

Full Linux regression (final source, from apps/api; source resolves the repository, not apps/api):

```powershell
$source = (Resolve-Path ../..).Path
docker run --rm --network none --read-only --tmpfs /tmp:rw,size=512m `
  --mount "type=bind,source=$source,target=/workspace,readonly" `
  --workdir /workspace/apps/api --env PYTHONDONTWRITEBYTECODE=1 `
  --entrypoint python buddyweb-ui-blockers-ci:20261031 `
  -m pytest -q -o cache_dir=/tmp/pytest-cache --basetemp=/tmp/chatbot-integrated-suite
```

Final:1,855 PASS/37 explicit live-environment SKIP/one existing AnyIO deprecation warning,187.69s.
Initial wrong-root collection and50ms recovery-budget failures are not PASS evidence. Exact fixtures
were restored byte-for-byte before final verification; only test timeout/comment calibration differs.
Linux CI image is an existing local cached development fixture; production artifact was independently
built and run above. No database/Redis/live/provider environment was enabled. c64 changes only frontend/documents;
backend tree, CI and dependency pins are identical, so the final backend/image evidence remains valid.
After c64 advancement:129 focused chatbot/Event tests PASS; final complete frontend920/91files
PASS,633.75s; both ON/OFF builds and static checks PASS. Demo-exclusion scan18files/10markers PASS. Two .mjs working-copy CRLF normalizations produce no Git content diff.

Evidence files retained locally: preservation/integration-manifest/integrity/load/linux-artifact JSON;
API focused/static/audit/build/full Linux logs; web full/focused/static/audit/ON-OFF build logs.
These are review aids, not committed raw operational logs. Hosting metadata was filtered/read-only;
no real personal request log, env secret, deploy hook or account information is recorded.
