# Documentation coverage audit

Audit date: 2026-10-17. Baseline `794a1a4530f3770f4e67b2863ebf658c8c0078d2`.
The initially clean `main` has 211 reachable commits, earliest `cd11dcf` on 2026-09-09.
The repository is not shallow. Available local branches contain eight commits outside main;
their existence is not evidence of delivery. No fetch, cloud access or Production check ran.

## Method and coverage meaning

Inventoried tracked Markdown, migrations, source modules, tests, CI and Git subjects/diffs.
Read control-plane records first, then targeted implementations and milestone records.
The [inventory](EVIDENCE_INDEX.md) lists all baseline Markdown records and migration paths;
it is a discovery inventory, not a claim that every legacy paragraph was revalidated.
The immutable legacy plan was not read end to end. Task extracts supplied historical detail.
Significant milestones were grouped rather than inventing a narrative for every small commit.

“Fully documented” below means sufficient source-linked explanation and retained records
for the stated boundary; it never means exhaustive history or current runtime acceptance.

| Domain                              | Before audit                                                  | Evidence and result after audit                                                                       |
| ----------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Frontend foundations and auth       | Fully documented in task slices, poorly discoverable          | New route/state map and auth walkthrough; links to source and tests                                   |
| Profiles/avatar/preferences         | Fully documented implementation; Production edit gate partial | Completion, optimistic edits and private-media lifecycle explained; Home University gate remains open |
| Matching/invitations/chat           | Fully documented contracts; overview outdated                 | End-to-end flow, score math, eligibility, atomic acceptance and recovery connected                    |
| Events                              | Partial/conflicting summaries                                 | Current null schedule, Audience removal, shared slider and independent flags verified in code         |
| Database                            | Partial narrative; substantial migration/test evidence        | Entity/integrity map and complete 0001–0022 evolution grouped; Production 0022 remains unknown        |
| Infrastructure/email                | Substantial runbooks and dated evidence                       | Current topology separated from Cloud Run investigation, staging and earlier proposals                |
| Security                            | Fully documented scoped controls and acceptance               | Threat boundaries linked; no claim of complete penetration testing                                    |
| Tests                               | Substantial task-specific acceptance                          | Current CI mapped; historical counts labeled and not rerun                                            |
| Incidents and decisions             | Partial, scattered across tasks/operations                    | Consolidated incident and ADR references with explicit unknown causes/alternatives                    |
| Reconstruction and student learning | Missing connected reference                                   | Architecture, workflows, progression and evidence-grounded interview guide added                      |
| Incremental maintenance             | Missing audited-SHA protocol                                  | Baseline and category-based update process added                                                      |

## Conflicts and outdated records

1. Root README said Matching was unimplemented, Event routes absent, database head 0007 and
   hosted infrastructure unprovisioned. Source and dated Production records disprove these
   statements. This audit corrects those overview sections and links to this reference.
2. [Implementation history](../implementation/history.md) still calls static Events the current
   launch and retains a Python 3.14 regression exception. Newer `EVS-007` and Event release
   records supersede that snapshot. History is preserved rather than silently rewritten.
3. [Decision log](../implementation/decision-log.md) retains historical PUBLIC-only slider and
   shared-flag wording. Its independent-flags section supersedes the shared switch; the newer
   Audience task and current query supersede PUBLIC-only filtering. New ADRs explain both.
4. The lightweight plan and index retain `EVENT-OPTIONAL-PUBLISH-001` as NOT DEPLOYED, and CTA/
   Matching tasks as LOCAL ONLY, while the later exact `e4624c0` release is their descendant.
   Git ancestry proves code inclusion, not that every ancestor's feature was independently
   smoke-tested. Preserve individual acceptance limits; reconcile deployment labels during
   the next release review. No historical task completion is overwritten here.
5. Older Render runbook blocker text still includes absence of backend rollback; the dated
   October 10 release establishes a retained rollback point. The private backup failure,
   unnamed recovery owners and missing post-repair hold remain open.
6. Production status contains an early static-bundle table alongside later public-on release
   sections. Treat dated sections as observations at their own time, not one simultaneous
   snapshot. This audit makes no fresh Production-state assertion.
7. Branch `codex/disable-semester-reset-audit` includes `da46bfa` and recovery planning absent
   from main. Do not describe Reset as removed from the audited implementation.

## Missing and unreconstructable evidence

| Priority            | Gap                                                                                              | What would resolve it                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| P0 operational      | Production private Semester backup failed; exact root cause/repair not established by this audit | Separately authorized diagnosis and safe acceptance; existing failure record is preserved |
| P0 operational      | Named rollback/recovery owners and accepted hold duration missing                                | Owner decision recorded through the existing control plane                                |
| P1 release evidence | Production Alembic 0022 revision and some Render release identities absent                       | Authorized operator evidence; do not infer DB state from healthy API                      |
| P1 acceptance       | Home University edit/save/reload/clear/max-length gate open                                      | Focused owner acceptance, without repeating accepted display checks                       |
| P1 resilience       | Residual ACCEPT-001, SEM-008 and encrypted off-site DR rehearsal open                            | Missing scoped evidence/disposable restore under a separate task                          |
| P2 history          | Early frontend/design inputs before first commit and exact operator provisioning sequence        | Original artifacts or owner records; inaccessible history cannot be invented              |
| P2 rationale        | Some weights, stack choices and terse October 16 commits lack recorded alternatives/motivation   | Ask the author when needed; current behavior and diffs are known, intent is not           |
| P2 measurement      | No consolidated workload/performance baseline or longitudinal SLO results                        | A separately assigned measurement task                                                    |
| P2 delivery         | Gmail/Outlook rendering and a fresh real email send were not run for latest redesign             | Separate scoped acceptance; automated contracts are existing evidence                     |

The project can be reconstructed at the code/schema level from accessible history and lockfiles.
It cannot be reconstructed as an exact historical cloud environment or data snapshot from Git.
No personal authorship, outage duration, provider migration date or undocumented design rationale
is inferred solely from a commit subject.

## Audit completion boundary

All requested domains now have populated explanations and cross-references. Historical
reconstruction remains partial where evidence above is missing. Documentation validation results
are recorded in [the audit task](../implementation/tasks/DOC-KNOWLEDGE-001.md).
Application regression and accepted Production gates were intentionally not repeated for this
documentation-only change. The original archive, source, migrations and runtime configuration
are unchanged.
