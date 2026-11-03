# Phase 3.6 — proposed release and rollback runbook

## Current candidate continuation —2026-11-03

[Phase3.5.1](PHASE_3_5_1.md) closes safe Git integration and the actual local Linux artifact gap.
Candidate branch codex/chatbot-phase35-integration has approvedc64 as its parent; resolve exact SHA
with git rev-parse. Prior a1aa is reachable through codex/chatbot-phase35-preserved. Local main9ec
and all original user files remain untouched. Do not repeat the old merge step below.

**Still NOT EXECUTED / NO-GO.** Finish finalc64 EN/DE browser/screenshot/device/SR acceptance; verify actual
Render peer/header sanitization and platform log retention with safe synthetic evidence; inspect
only needed effective worker/env/quota settings without exposing secrets. Obtain explicit acceptance
of process-local NAT/restart limits, confirm retained secure rollback eligibility and current CI.
Fresh current targets: Vercel dpl_9qn8NtQWwGGer9kNxQGn9QFkCyyK/mainc64 and Render
dep-dbhhnpp42hec73cgjsu0/main642fc11. Settings read-only: AutoDeployOFF, PRPreviewsOFF,
apps/api/./Dockerfile/context `.`, no command/predeploy overrides, /api/health/live.

No push/deploy/env/config change is authorized here. Before a future push, re-fetch safely, compare
ancestry/current remote and request exact SHA/branch publication scope, stating Vercel main push
can automatically deploy Production while Render stays manual. Green hosted CI/Preview and a
separate release approval are required before following the sequence below. Keep both chatbot
flags and AI OFF initially; backend flag changes require restart, frontend changes require rebuild.
Actual rollback remains untested; recheck target eligibility at the time of a separately approved
incident action. No schema/migration/data change is needed for this chatbot release.

Prepared2026-11-01 for [Phase 3.5](PHASE_3_5.md). **NOT EXECUTED. Current decision NO-GO.**
This document is a future procedure, not authorization to publish, change env, migrate or roll back.

## Before selecting a release

1. Obtain explicit approval for an exact integrated SHA/branch, Vercel/Render executors and rollback
   decision owner. Preserve all dirty work/worktrees; resolve local-main 6 / remote 4 divergence only
   through a separately authorized integration. Never publish the detached old main 9ec snapshot.
2. Start from the current approved UI/security baseline. Retain released Pillow 13, Zod 4.6.6 and
   dependency fixes; integrate chatbot files/package-data, App/transport/locale additions and the
   two Phase 3.5 fixes without overwriting the new UI/security source. Review the combined diff.
3. Run exact candidate backend/frontend CI, current runtime/dev audits with only explicitly retained
   exceptions, TypeScript/lint/format/tests/build/wheel. Build/run the actual pinned Python 3.12 Linux
   Docker artifact; record installed pins and non-root user. No new dependency/service/billing.
4. Check local/remote ancestry and clean exact candidate immediately before publication. Verify
   canonical source hash/174 actual passages, nine JSON hashes and owner/conflict labels inside
   the built container from an unrelated cwd, not only the checkout. Do not add test facts.
5. Reconfirm correct Vercel project/root/Vite/Node 24 and direct HTTPS API base ending `/api`;
   exact allowed frontend CORS origins and safe error/Retry-After headers. Do not add a second proxy.
6. Inspect Render's effective Docker/start overrides, pre-deploy command, worker/instance count,
   health paths and AutoDeploy setting. No database migration is required by the chatbot; do not
   attach migrations or change existing data/email/account settings as a release shortcut.
7. Establish actual socket peer ranges, complete proxy chain and header sanitization guarantees.
   Validate documented trusted/untrusted cases without raw personal-IP logging. Keep restrictive
   allowlist until established; never set forwarding trust to `*` or trust the leftmost raw header.
8. Verify effective `--no-access-log` and the app's metadata-only logger. Inspect platform/edge log
   policy and retention using synthetic sentinels; ensure query strings/POST bodies/cookies/tokens
   are not retained unnecessarily. If provider log behavior cannot be made acceptable, keep NO-GO.
9. Confirm zero-cost existing account/plan/quota limits, no paid autoscale/upgrade, and explicit
   acceptance of process-local/NAT/restart limits for expected load. No chatbot Redis is required.
10. Reconfirm safe retained frontend/backend rollback deployments on fixed security versions.
    Dated evidence lists frontend5a7bb90 (current) or retained fixed e1a2cc59 and backend642fc11;
    these are references to recheck, not a promise that every old deployment remains eligible.

## Controlled deployment sequence — only after separate approval

1. Publish only the exact approved combined commit through the existing release workflow. Identify
   any Vercel automatic Production trigger before pushing; a push can be a deployment action.
2. Deploy compatible frontend/backend code with **VITE_CHATBOT_ENABLED=false**, **CHATBOT_API_ENABLED=false**,
   **CHATBOT_AI_ENABLED=false**. Verify fresh build/runtime flag values without exposing secrets.
   Retain Render AutoDeployOFF unless the separately approved release explicitly changes it.
3. Check existing live/readiness and public application routes. Verify chatbot UI hidden and endpoint
   503/disabled (an older backend may return404 until compatible code is deployed). Record SHA/image.
4. Activate only backend CHATBOT_API_ENABLED=true via the approved env+restart/redeploy procedure,
   leaving AI false and frontend hidden. Confirm every process loaded the new settings/source.
5. Perform the low-volume smoke below. Stop on critical errors; report and obtain recovery approval.
6. Build/deploy the frontend with VITE_CHATBOT_ENABLED=true and the confirmed direct HTTPS API base.
   It is a new Vite build, not a runtime dashboard toggle. Confirm the actual served build and route.
7. Repeat low-volume UI/EN-DE/source smoke, existing app health and owner device/SR acceptance.
   Observe the owner-agreed hold duration and monitoring signals; do not invent a completed interval.

## Low-volume Production smoke — proposed, not run in Phase 3.5

Use public/synthetic questions only, with no personal data, credentials or external AI calls:

| Check | Expected |
| --- | --- |
| Anonymous `How do I register?` | Verified existing FAQ/citation; no private account lookup. |
| Anonymous `Where can I eat?` | Qualified owner evidence, actual source hash/lines, no current-verification claim. |
| Anonymous `Wäscherei` | German conditional qualification with explicitly untranslated source. |
| `What is the weather on Mars?` | Unsupported; no unrelated fact/citation. |
| Source details | Correct canonical version, verified vs owner/conflict labels and safe references. |
| Existing health/public routes | Liveness/readiness and approved existing anonymous application paths stay healthy. |
| Disabled/unavailable | Confirm in the gated-off stage; test UI treatment in isolated local/approved preview rather than causing a Production outage. |

Do not generate rate-limit/load/abuse traffic against Production. Reuse local429/resource evidence;
inspect real operational metrics if they occur. Do not log in or create records through automation
unless separately authorized; owner performs applicable User/Admin and real-device/SR acceptance.

## Emergency disablement

1. With explicit incident authorization, set backend CHATBOT_API_ENABLED=false using existing Render
   controls and restart/redeploy. Wait for every worker/instance to return503/disabled; cached settings
   do not change merely because a shell variable or dashboard value was edited. Running work may
   finish during shutdown. The flag is independent of a frontend rebuild, but is not instantaneous.
2. Confirm liveness and unrelated application health; enabled frontend should show friendly
   unavailability, not raw errors. Keep CHATBOT_AI_ENABLED=false throughout.
3. Rebuild/redeploy frontend with VITE_CHATBOT_ENABLED=false to remove the launcher if needed.
   Hiding the frontend alone does not secure/disable the endpoint; direct callers can still reach it.
4. A provider stop/suspend action affects the entire backend and is a separate owner decision;
   it is not the default chatbot kill switch. Never alter billing or unrelated services automatically.

## Rollback — separate explicit recovery approval required

- Prefer disabling the new backend feature first. Restore a retained security-fixed frontend with
  chatbot hidden, then the retained fixed backend if necessary. Confirm exact SHA/image and current
  provider rollback eligibility; frontend rollback tools can affect future domain assignment.
- Do not roll back to pre-Pillow/Zod fixes or main 9ec just because it contains chatbot history.
  Preserve current security requirements and unrelated application changes.
- For knowledge-only mistakes, restore the known-good canonical file in a new reviewed commit on
  the fixed backend baseline, keep its provenance bytes, validate hashes/questions and redeploy.
  Never depend on editing an ephemeral deployed filesystem. Local source reload is not a CMS.
- Repeat health/public-route and tiny EN/DE/verified/owner/miss smoke on the rolled-back compatible
  contract. Record the actual source hash, mode, release IDs, outcome and owner-approved hold.
- No automatic rollback, source reset, migration rollback or user-data restoration is authorized
  here. Record failure evidence and the explicit decision before a consequential recovery action.
