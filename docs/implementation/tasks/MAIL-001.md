# MAIL-001

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** -
**Dependencies (latest extracted):** BE-004, EMAIL-001; Backend + Database + Infrastructure.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6922-6932

#### MAIL-001 — Transactional email provider and outbox foundation

- **Status:** **Done 2026-09-24; hosted transport repository work added 2026-09-25 under OPS-002.** MAIL-001 adds the private outbox, provider-neutral contract with a Resend adapter, explicit template allowlist, bounded leased Python worker and server-only configuration. OPS-002 reuses those contracts through migration `0010`, the Edge Function and Cron SQL; it does not rewrite MAIL-001. Only `email_verification.requested` is implemented today. Invitation and accepted templates/events remain owned by INV-008/009.
- **Purpose:** Decouple committed business state from fallible delivery.
- **Scope / source:** `models/transactional_outbox.py`, migrations `0009`/`0010`, `services/email_outbox.py`, `services/email_provider.py`, worker command, `supabase/functions/email-worker`, `supabase/cron/email-worker.sql`, server-only config and `docs/operations/supabase-email-worker.md`.
- **Dependencies / ownership:** BE-004, EMAIL-001; Backend + Database + Infrastructure.
- **Security:** provider key server-only; recipient/body/provider errors redacted; unique event idempotency keys; no arbitrary template selection; private schema and function execute rights are withheld from PUBLIC and the Supabase `anon`, `authenticated` and `service_role` Data API roles.
- **Acceptance / DoD:** transaction inserts one outbox row; default batch 20/max 100, five-minute owner lease, max five attempts, 1/2/4/8-minute retry and terminal observability are preserved; provider failure cannot roll back originating state; no heavyweight broker or always-on hosted email process is added.
- **Tests/gates:** fake-provider success/failure, unique-key duplicate prevention, overlapping `SKIP LOCKED` claims, owner-only finalization, lease recovery, bounded batch, retry/terminal states, config fail-closed and log-redaction tests.
- **Non-goals:** marketing/bulk email or pricing commitment.


## Cross-reference occurrences outside extracted headings

- Legacy line 29: > **v2.5 — 2026-09-26, MAIL-001 deployment audit (historical state, superseded by v2.6):** The repository implementation and current official provider documentation were re-audited without changing application code, migrations or infrastructure. Production email delivery is controlled by \`application/backend → app_private.transactional_outbox → Supabase Cron (one minute) → Supabase Edge Function email-worker → Resend\`. Google Cloud VM/e2-micro, a paid Render Background Worker and any always-on hosted Python email worker are rejected alternatives, not production dependencies. The Python worker remains only for local development, debugging and a manually activated fallback after Cron is disabled. At that audit timestamp OPS-002 still awaited account-owned deployment acceptance; the completed state is recorded by v2.6 and the OPS-002 evidence.
- Legacy line 6850: | MAIL-001 (**Done 2026-09-24**) | Provider + transactional outbox | BE-004, EMAIL-001 | Commit independent of delivery; retry/idempotency | Fake-provider/lease/failure tests |
- Legacy line 6851: | EMAIL-002 (**Done 2026-09-24**) | Request/resend verification | EMAIL-001A, MAIL-001, AUTH-020 | Current address only; rate-limited; old token superseded | API/rate/concurrency tests |
- Legacy line 6869: | INV-003 | Send invitation API | INV-002, REC-003, MAIL-001 | Trimmed plain text; ≤500 non-whitespace runs and ≤10,000 code points; max 30 outgoing PENDING | Schema/boundary/CSRF/rate/race tests |
- Legacy line 6874: | INV-008 (**Done 2026-10-01**) | Invitation email notification | INV-003, MAIL-001 | Post-commit retryable Open Invitation email | Template/outbox/delivery tests |
- Legacy line 6875: | INV-009 (**Done 2026-10-01**) | Accepted email + safe deep links | INV-005, MAIL-001 | Start Chatting email and allowlisted \`returnTo\` | Template/outbox/link tests |
- Legacy line 6892: | OPS-001 | Local Redis/worker/config foundation | MAIL-001 | Local Redis, worker/scheduler, health/readiness, no heavyweight queue | Startup/failure/compose tests |
- Legacy line 6938: - **Dependencies / ownership:** EMAIL-001A, MAIL-001, AUTH-020; Backend.
- Legacy line 7196: \`INV-002\`, \`REC-003\` and \`MAIL-001\` dependencies are DONE. \`Send Invitation\` and the real V2
- Legacy line 7380: - **Dependencies / ownership:** INV-002, REC-003, MAIL-001; Backend + Database.
- Legacy line 7514: - **Dependencies / ownership:** INV-003, MAIL-001; Backend + Infrastructure.
- Legacy line 7545: - **Dependencies / ownership:** INV-005, MAIL-001; Backend + Frontend + Infrastructure.
- Legacy line 8091: - **Dependencies / ownership:** MAIL-001; Infrastructure + Backend.
- Legacy line 8102: - **Dependencies / ownership:** EMAIL-003, OPS-001; Infrastructure + Operations. Downstream, OPS-003 depends directly on OPS-002; SEM-002 depends on OPS-003 and therefore SEM-004..007 and ACCEPT-001 depend indirectly on this gate. Invitation/accepted email tasks retain their MAIL-001 dependencies and their functional requirements; this deployment decision does not remove or weaken them.
- Legacy line 8156: EMAIL-001 → MAIL-001
- Legacy line 8158: (EMAIL-001A + MAIL-001) → EMAIL-002
- Legacy line 8171: (INV-002 + REC-003 + MAIL-001) → INV-003
- Legacy line 8193: MAIL-001 → OPS-001
- Legacy line 8204: 1. \`EMAIL-001\` first; then \`EMAIL-001A\`, \`MAIL-001\` and \`AUTH-V2-001\` as their dependencies permit.
- Legacy line 8215: - PREF-001/002/003 can run alongside EMAIL-001/001A/MAIL-001/EMAIL-002.
- Legacy line 8222: The task-level dependency graph is unchanged by the worker-provider decision: \`MAIL-001 → OPS-001 → OPS-002 → OPS-003\`. The new order is entirely inside OPS-002. If a Supabase Free-plan gate fails, stop and report the constraint; do not substitute a paid worker.
- Legacy line 8304: The v2.6 amendment reconciles OPS-002 evidence and implements only OPS-003 operational telemetry, monitoring SQL, runbooks and tests. \`MAIL-001\` retains the private transactional outbox, provider/template boundaries, bounded Python fallback and server-only configuration. OPS-002 retains the least-privilege Edge claim/finalize functions and scheduled Edge transport. No PREF/REC/INV/BUDDY/CHAT behavior, migration or provider topology is introduced. Before committing, inspect the final diff and confirm that no generated build/cache artifact or secret became tracked.
