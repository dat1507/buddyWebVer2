# CHATBOT-READY-001 — Phase 3.5 local readiness/security validation

**Assigned:** 2026-11-01 (Asia/Saigon), explicit owner pasted request.
**Status:** LOCAL REVIEW COMPLETE — RELEASE NO-GO / PARTIAL.
**Baseline:** local main 9ec31fbcf0aadfb5347bd9eba76c2f362b205904, isolated detached managed checkout.

Primary pillow-security-fix checkout has unrelated dirty work. Preserve all files/branches/worktrees.
Fresh remote main 5a7bb90 and local main diverge6/4. Vercel directly confirms frontend Production5a;
dated owner evidence records Render 642fc11/AutoDeployOFF. No integration/reset/rebase is authorized.

Independently inspect/fix proven chatbot readiness defects; validate target runtime, routing/proxy,
privacy/logging, resource bounds, KB artifacts/reload, safe flags and built frontend/API local flow.
Preserve exact canonical source, all JSON/vocabulary/facts/provenance. Add focused negative security
checks, modest loopback load, responsive/keyboard/a11y checks; retain manual/Production limits.
Produce PHASE_3_5 report/gate matrix/config/evidence and Phase 3.6 release/rollback runbook.
One scoped local detached commit after verification. No branch movement/push/deploy/Production
chatbot requests, cloud/env/account/DB mutation, inference, paid resource or new dependency.
Critical integration and undocumented hosting proxy/logging behavior remain NO-GO unless verified.

## Acceptance — 2026-11-01

Two narrow fixes: disable raw Uvicorn access logs in Docker CMD, and explicit/safe UTF-8 CLI I/O.
Focused tests cover proxy boundaries, TTL/capacity/process counters, restart flags/log privacy,
container command and literal HTML plus CLI encoding. No factual/JSON/vocabulary/dependency changes.

Final Python 3.12.10 Windows backend 1851 PASS/79.89s; frontend 101 PASS/4 files. Ruff/format/mypy 129,
TypeScript/affected lint/format, ON/OFF builds, wheel/unrelated-cwd/two-process hash checks PASS.
37 runtime pins/438 installed frontend package versions match this old snapshot's locks. One existing
deprecation/large-entry warning; no Linux Docker build/run because daemon unavailable.

Built frontend -> packaged guarded API -> sources -> actual UI PASS for verified/owner EN-DE/miss,
429 cooldown and503 disablement/all four flag combinations.36-request local load:22success,6quota,
4concurrency rejections plus expected validation errors;4/4 concurrent liveness200, max 469.16 ms.
Two OS API processes independently200 then429 for same IP and same source hash. All application
external/provider/private DB counters zero; owned servers stopped and browser overrides restored.
EN/DE1440/768/390/320 panel bounds, native keyboard/focus/modal/reduced-motion/source rendering
checked. Old baseline German Landing 329 px at 320 also occurs OFF; unrelated. Physical keyboard/SR
remain manual. Source 22129 bytes/431 lines/174 passages and all old corpus/metadata unchanged.

Readiness documentation, command record and proposed Phase 3.6 runbook complete. Release NO-GO:
no approved integration with newer UI/Pillow/Zod fixes, no final combined Linux/CI artifact, and
actual Render proxy/routing/edge logging/env/worker/rollback evidence remains unverified.
Primary dirty work and main/remote histories were preserved, no integration performed. One focused
local detached commit only, no branch movement/push/deploy/Production chatbot request/cloud change,
new dependency/service, inference, billing or additional operating cost. No next task assigned.

[Report/gate matrix](../../project-knowledge/chatbot/PHASE_3_5.md),
[exact commands](../../project-knowledge/chatbot/PHASE_3_5_COMMANDS.md),
[unexecuted release/rollback runbook](../../project-knowledge/chatbot/PHASE_3_6_RUNBOOK.md).
