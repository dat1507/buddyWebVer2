# BuddyWebv2 technical knowledge base

Audited 2026-10-17 (Asia/Saigon). Source baseline:
`794a1a4530f3770f4e67b2863ebf658c8c0078d2` on `main` (211 reachable commits).
This is a documentation audit, not a fresh runtime or Production acceptance.

Start with [Architecture](ARCHITECTURE.md), then follow the
[learning progression](learning/README.md). For historical questions use the
[milestones](CHANGELOG.md) and [evidence inventory](EVIDENCE_INDEX.md). For uncertainty,
read the [coverage audit](DOCUMENTATION_AUDIT.md) before relying on a claim.

| Reference                                      | What it explains                                                             |
| ---------------------------------------------- | ---------------------------------------------------------------------------- |
| [Frontend](frontend/README.md)                 | Routes, state, API client, localization, responsive UI                       |
| [Backend](backend/README.md)                   | Request handling, authorization, services and endpoint map                   |
| [Workflows](WORKFLOWS.md)                      | Registration, profiles, recommendations, invitations, chat, Events, Semester |
| [Database](database/README.md)                 | Relationships, integrity, migration evolution and retention                  |
| [Infrastructure](infrastructure/README.md)     | Local/hosted topology, workers, release and recovery boundaries              |
| [Security](security/README.md)                 | Cookie sessions, CSRF, capabilities and privacy                              |
| [Testing](testing/README.md)                   | Test layers, regression scenarios and evidence limits                        |
| [Incidents](incidents/README.md)               | Verified problems, investigations, fixes and open risks                      |
| [Decisions](decisions/README.md)               | Evidence-backed lightweight ADRs and consequences                            |
| [Interview guide](learning/INTERVIEW_GUIDE.md) | Project-specific model answers and exercises                                 |
| [Update protocol](UPDATE_PROTOCOL.md)          | Incremental review from the last audited SHA                                 |

## Reading evidence correctly

**Code-confirmed** means the audited source implements the described behavior. It does
not prove a deployed configuration or a successful real transaction. **Recorded acceptance**
means a linked, dated record reports a check; this audit did not repeat it. **Inference**
means a conclusion supported by structure or diffs without a recorded rationale.
**Unknown** identifies evidence still needed. Planned or branch-only work is never delivered
`main` behavior.

The control-plane precedence remains [AGENTS.md](../../AGENTS.md). Consult
[Production status](../implementation/production-status.md) for the latest dated deployment
observations, [handoff](../../SESSION_HANDOFF.md) for the current boundary, and
[implementation plan](../../implementation-plan.md) for task status. This knowledge base
explains implementation; it does not grant permission to operate Production.

Current `main` includes Matching, invitations, chat and canonical Event APIs. AI assistant
and campus routes remain placeholders. The About redesign is locally accepted at the
baseline; its Production deployment is not recorded. Production evidence is latest for the
email release at `e4624c0`, not for every subsequent local commit. Ancestor changes may be
carried by later releases even where an individual task still says NOT DEPLOYED; see the audit.

For reconstruction, read source and dated evidence together. A clean Git checkout alone
cannot reconstruct cloud settings, private data, historical secrets or operator decisions.
