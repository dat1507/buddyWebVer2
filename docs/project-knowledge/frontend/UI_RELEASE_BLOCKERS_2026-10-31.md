# Final UI blocker disposition — 2026-10-31

**LOCAL GATES COMPLETE — READY TO REQUEST CANDIDATE PUBLICATION.**
**NO-GO for Production until exact-SHA hosted CI/Preview acceptance and separate owner approval.**
Accepted UI c1e04e9; preserved candidate0a43d4e; remediation is its local descendant on codex/ui-release-rc.
Final commit and exact diff are recorded in primary handoff and `.local/ui-release-blockers/release-manifest.json`.
Worktree: `C:/Users/phuoc/Downloads/buddyWebVer2/.local/worktrees/ui-release-rc`.

## Scope and security

Reviewed all59 original paths:50 presentation/accessibility/test paths, one verification scanner,
eight control/knowledge documents. All266 application source hashes remain identical to0a43d4e.
The new application-area diff is exactly package.json, package-lock.json and requirements-dev.lock;
there are no runtime/auth/API/route/schema/feature/visual changes. Six unpublished main commits,
other UI branches/worktrees, primary dirty work and .agents remain untouched. Zod4.6.6/Pillow13 intact.

Frontend:18 of19 unique advisory IDs fixed with Vite8.2.4, Vitest5.0.3, selector-parser6.1.5,
source-map-js1.2.2 and undici7.30.1. npm production audit0. Remaining14 moderate package entries are
one minimatch advisory: scoped trusted-lint-input exception, no incompatible major override.
Backend:17 reported rows deduplicate to16 IDs; all fixed by dev-only certifi2026.10.18,
msgpack1.2.3, filelock4.2.1 and setuptools84.1.0. Explicit runtime37/dev81 lock rows audit0.
[Unique advisories, affected pins, exposure and residual-risk conditions](UI_RELEASE_SECURITY_FINDINGS_2026-10-31.md).

## Verification and count reconciliation

| Gate                                | Result                                                                                                                                                                                      |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Final full frontend                 | PASS833/88,112.46s, rerun because Vite/Vitest changed.                                                                                                                                      |
| Backend with patched dev tools      | PASS1421/37 opt-in SKIP,53.33s; separate image/security93 PASS.                                                                                                                             |
| Static/package checks               | Types/full ESLint/full Prettier, pip check/Ruff/mypy294, graph/heads and wheel/sdist PASS.                                                                                                  |
| Generated production/demo boundary  | Both normal/demo-flag builds PASS;23 files identical to each other AND prior browser-verified artifact;10 demo markers absent.                                                              |
| Browser/integration/responsive/a11y | Reused exact identical output:69 real API assertions, actual profile/Event flows, final18 loaded EN/DE viewport axe cases0 violations and prior42 cases with error-state limits documented. |
| Runtime security                    | PASS0 npm/0 Python; full Python dev0; npm dev14 entries accepted only as the one scoped tooling exception.                                                                                  |
| Old ADMIN opt-in fixtures           | Known11 PASS/2 FAIL retained; scoped release exception, follow-up below.                                                                                                                    |
| Old fresh-install migration         | Known FAIL retained; scoped release exception, follow-up below.                                                                                                                             |
| Exact candidate hosted CI           | UNVERIFIED: branch absent remotely; no push/dispatch/deployment performed.                                                                                                                  |

924 =833 retained tests +7 demo engine +40 chatbot client +18 chatbot entry +26 chatbot widget.
The four excluded files were executed separately:91 PASS. Remaining88 file inventories match;
only two existing files differ from accepted UI for accessible-name assertions. Dry discovery lists
unexpanded definitions, so executed JSON counts were used. No tests were weakened to lower the count.
Initial package.json formatting failure was corrected with existing Prettier; final formatting PASS.
All other tests/static/build results remain valid because formatting changed no dependency semantics.

## Task2-authorized exceptions — this frontend-only release

ADMIN test helpers promote a registered USER but keep semester_id; the intended model constraint
rejects that invalid fixture before auth checks. Production valid ADMIN behavior is unchanged;
actual valid Admin API integration passed. No runtime auth/business rule or fixture was edited here.
Follow-up: [TEST-AUTH-ADMIN-FIXTURES-001](../../implementation/tasks/TEST-AUTH-ADMIN-FIXTURES-001.md).

Revision0022_public_event_visibility_default is36 characters versus default VARCHAR32 version table.
The earlier unmodified fresh-install failure remains a failure; no assertion was hidden. Runtime
code, migration graph/IDs, Docker startup, pyproject and requirements.lock are unchanged; no migration
is required or executed for this UI release. Prior fixture-only widening is not clean-install proof.
Follow-up: [OPS-ALEMBIC-VERSION-LENGTH-001](../../implementation/tasks/OPS-ALEMBIC-VERSION-LENGTH-001.md).

These are justified release exceptions under the owner's explicit Task2 instruction, not general
test waivers. Invalidate them if backend auth/models/schema/runtime dependencies change, migration
execution or fresh database provisioning becomes part of release. Do not rename applied revisions
or weaken ck_users_role_semester. No Production database/schema/data change is authorized/performed.
Remaining tooling follow-up: [SEC-DEV-MINIMATCH-001](../../implementation/tasks/SEC-DEV-MINIMATCH-001.md).

## Publication effects — permission still required

Fresh origin/main remains e1a2cc59. Only .github/workflows/ci.yml exists: every branch push runs
Frontend and Backend; contents:read; no deployment/migration job. Default CI audits runtime deps;
no workflow or threshold changed. The candidate branch is not on origin. A normal non-force push of
only codex/ui-release-rc is expected to create that branch, run these two jobs and create Vercel Preview.

Fresh read-only Vercel UI: correct buddy-web-ver2 project; Production tracks main, auto-assign domains
enabled; Preview tracks all unassigned branches and has no attached custom domain. Render remains
Live642fc11/main, AutoDeployOff, PR PreviewsOff, no pre-deploy override. Candidate publication therefore
does not update main, Production domains, Render or databases. No push/PR/merge/provider setting change.

The Vercel connector lacked scope access; existing browser UI verified triggers without new grants.
Preview API base remains UNVERIFIED because reveal required owner step-up; request was cancelled.
No Preview-specific public/Admin Event variables are listed, so existing defaults apply. Do not use
Preview for authenticated/data-writing tests until its isolated API target and needed Preview flags
are separately verified/authorized. This limitation does not prevent safe branch CI/static Preview
publication; Production API/flags were already verified in the prior report and local build tests.

## Conditional Production plan

1. Obtain explicit permission for exact candidate-only branch push and automatic Preview/CI.
2. Observe green Frontend/Backend at that SHA and Vercel Preview; review safe anonymous pages.
   Any authenticated Preview acceptance requires verified isolated API targeting first.
3. Present exact immutable release SHA, reviewed diff, exceptions and fresh recovery eligibility;
   request separate Production approval. No main update or Production deploy before that approval.
4. If later approved, use a non-force update based on current origin/main in isolation; preserve
   local main9ec and six unpublished commits. Vercel main deployment is frontend-only. Keep RenderOff;
   no backend deploy or migration. Recheck current e1 security deployment as recovery target; avoid f88
   which lacks the Zod fix. Revalidate Production environment values because Preview defaults differ.

Stop here. Sanitized evidence: primary `.local/ui-release-blockers/`; prior integration/browser proof
in `.local/ui-release/`. No new database/Storage fixture, secret, Windows trust or Production operation.
