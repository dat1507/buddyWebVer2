# Events Recap local CI-only suppression - 2026-11-04

**READY for separately authorized CI-only branch publication. Production NO-GO.**
Inputc92e64469c4e28886aad6b6fe2e7cd0cb74de5d3 was clean on codex/events-recap-rc before edits.
Owner explicitly authorized this local configuration change and one local commit. No push,
Preview, deploy, Production migration/data write, cloud setting, billing or infrastructure change.
Final exact SHA is the commit containing this report, recorded in the delivery message.

## Complete patch and configuration assessment

The complete prepared proposal has one hunk adding ONE configuration entry to apps/web/vercel.json:

```json
"git": { "deploymentEnabled": { "codex/events-recap-rc": false } }
```

Patch targets no other file. Verified apply-check first, then applied locally with
`git apply --ignore-space-change docs/operations/events-recap-ci-only-proposal.patch` for Windows
CRLF context. Prettier normalized file formatting; final diff still contains exactly that one added
line. All prior configuration entries compare identically after removing the new git object:
rewrites, security headers, schema declaration and all unrelated keys. No environment variable,
API endpoint, application source, workflow, lockfile or Production setting changed.

Fresh read-only dashboard observation confirms Vercel project buddy-web-ver2 root apps/web, Vite,
Node24, no install/build override, Ignored Build Step Automatic. This is the project's only tracked
Vercel configuration file; no root vercel.json, vercel.ts/toml alternative or other matching rule.
Production tracks main. Preview remains enabled/all unassigned branches/no domains attached.
Render dashboard reconfirms branchmain, livec0687ba, Auto-DeployOFF. No Save/deploy control used.

Official [Vercel Git configuration](https://vercel.com/docs/project-configuration/git-configuration)
documents false branch suppression, unspecified branches defaulttrue, and any matching explicittrue
rule overridingfalse. The complete rule object contains only the exact RC branchfalse: no wildcard,
no overlappingtrue, no global disable. Installed minimatch evaluation plus documented precedence:

| Branch | Explicit matches | Automatic Git deployment |
| --- | --- | --- |
| codex/events-recap-rc | exactfalse only | disabled |
| main | none | eligible/defaulttrue |
| codex/events-recap | none | eligible/defaulttrue |

The defaulttrue for an unspecified branch is not a separate matchingtrue rule. Preview dashboard
tracking makes a branch eligible; the repository Git rule suppresses this exact branch's automatic
Git deployment. It does not modify main's existing Production tracking or custom-domain behavior.
This is a Git-trigger rule, not a ban on separately requested manual CLI/API deployments.

## Focused verification

- Original worktree clean/exactinput verified; complete patch reviewed and apply-checkPASS.
- JSON parse and official current Vercel schema **git-property fragment** validationPASS.
  Whole downloaded schema declares draft04 but includes numeric exclusiveMinimum in unrelated
  optional functions/service definitions. Full meta-schema validation failed on that upstream
  inconsistency; scoped changed-property validation passes, and all untouched config compares
  identically. No whole-schema PASS is claimed.
- PrettiercheckPASS. Local production build (`npm run build`)PASS; unchanged existing build advisories.
- Branch matcher/precedence matrix abovePASS; no overlappingtrue rule or alternative config.
- Existing frontend/backend/CI recorded hashes all unchanged; diff under apps/.github is only
  apps/web/vercel.json. Approved 8/8 UI and all application behavior preserved.
- Production demo exclusion16 build files/10 forbidden markersPASS. No API target or environment
  values retrieved, changed, inserted or exposed. No full test suites repeated.
- Current docs/task links,253 extracts/index links and git whitespace checksPASS.

## CI-only behavior and remaining uncertainty

Only tracked Actions workflow is .github/workflows/ci.yml, unchanged. Push and pull_request triggers
have no branch exclusions. contents:read. Jobs install locked deps, lint/type/test/build/audit and
validate Compose. New Recap migration tests use disposable runner-local PostgreSQL. No deploy,
Production migration, remote secret reference, workflow_dispatch or reusable deployment workflow.
Frontend package build is tsc/Vite; no deploy/API lifecycle hook. No tracked Render blueprint.
No deployment-capable repository automation was identified; account-level third-party Apps/hooks
are not exhaustively inventoried, as documented in the prior preflight.

Expected after separately approved exact-SHA push to codex/events-recap-rc:
GitHub CI executes; Vercel automatic Git deployment is suppressed; no Preview frontend is created;
Render remains pinned/Auto-DeployOFF; no Production alias/backend/database operation occurs.
A skipped/absent Vercel check is expected, not a failed frontend test. Existing old Preview URLs,
if any, are not removed by this local rule. Do not open/use any unknown-target Preview for testing.
Preview API/database/Storage isolation remains UNKNOWN but is not needed for this CI-only path
because the new branch deployment is suppressed. Actual provider enforcement and exact-SHA hosted
CI remain unobserved until authorized publication; local JSON parsing alone is not this assessment's
basis (official semantics + project-root/branch observations + full-rule inspection/matcher checks).

Separate push authorization must name the final commit, using only:

```text
git push origin <FINAL_SHA>:refs/heads/codex/events-recap-rc
```

No force push/main merge. Before executing that later instruction, recheck branch/SHA/clean state,
upstream changes and known provider settings if time/state has changed. After publication inspect
Actions against that exact SHA and confirm no Vercel Preview deployment or Production change.
Unexpected deployment: stop hosted interactions and investigate, with no automatic provider mutation.
No push is authorized by the current request and none was executed. Production remains NO-GO on
backup/restore, quotas/headroom/latency, advisory disposition and separate deployment approvals.

## Exact files changed in this single local commit

1. apps/web/vercel.json (sole configuration/application-tree change).
2. SESSION_HANDOFF.md.
3. implementation-plan.md.
4. docs/implementation/task-index.md.
5. docs/implementation/tasks/EVENT-RECAP-CI-ONLY-001.md.
6. docs/implementation/validation.md.
7. docs/implementation/production-status.md (dated read-only observations only).
8. docs/project-knowledge/frontend/README.md.
9. docs/project-knowledge/frontend/EVENT_RECAP_CI_ONLY_SUPPRESSION_2026-11-04.md.

Existing proposal patch and completed reports/history are unchanged. All original worktrees,
unpublished commits and approved featurebdcd082 remain preserved. Prior exact-SHA hosted
assumptions do not transfer to this new commit; application test evidence remains applicable.
