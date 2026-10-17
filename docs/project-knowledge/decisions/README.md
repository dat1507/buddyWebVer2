# Architecture decisions

These lightweight ADRs summarize confirmed choices and link to original authority. They do
not fabricate rejected alternatives or attribute choices personally to the repository owner.
Dates identify the accessible evidence, not necessarily the first discussion.

## ADR-01 — FastAPI owns authentication (accepted)

**Context:** protected student/Admin workflows need consistent session, role and capability
authority. **Decision:** custom private `users`, backend bcrypt/JWT cookie sessions, signed
CSRF and non-persisted sanitized frontend auth state. Supabase provides hosting/Storage,
not application Auth. **Alternatives:** Supabase Auth is explicitly not the selected system;
a comparative decision analysis is not retained. **Trade-off:** consistent backend domain
authority requires maintaining rotation, revocation, verification and rate-limit logic.
**Consequence:** deleting an application user cannot be reduced to deleting `auth.users`.
Evidence: `fced9f3`, AUTH tasks, [decision log](../../implementation/decision-log.md),
[actual account topology](../../operations/account-delete-001-production-2026-10-17.md).

## ADR-02 — Recommendation and consent replace Admin 1:1 assignment (accepted)

**Context:** current Buddy product uses student discovery and explicit recipient consent.
**Decision:** deterministic weighted recommendation, invitations, atomic acceptance, multiple
Buddies and one ACTIVE unordered pair; Admin monitors. **Alternative:** older assignment/run/
preview/publish contracts are superseded. **Trade-off:** explainable bounded scoring is simpler
than semantic/ML matching but cannot discover unmodeled similarity. **Consequence:** do not
revive superseded Admin matching controls or describe a recommendation read as assignment.
Evidence: [decision log](../../implementation/decision-log.md), REC/INV tasks,
[scoring](../../../apps/api/app/services/matching_scoring.py). Why the exact weights were
chosen beyond the confirmed contract is unknown.

## ADR-03 — PostgreSQL durability, Redis realtime acceleration (accepted)

**Context:** disconnections/retries must not lose conversation truth. **Decision:** persist
messages/read state, enforce send idempotency, fan out through Redis/WSS and recover via REST.
**Alternatives:** no complete transport comparison is recorded. **Trade-off:** clients must
reconcile rather than treating a connected socket as complete history. **Consequence:** Redis
loss can degrade realtime without justifying corruption of stored messages.
Evidence: CHAT tasks, [chat service](../../../apps/api/app/services/buddy_chat.py),
[realtime service](../../../apps/api/app/services/chat_realtime.py).

## ADR-04 — Outbox with Cron/Edge mail delivery (accepted Sep 25 onward)

**Context:** email must follow committed domain changes under cost constraints.
**Decision:** database outbox, hosted Supabase Cron/Edge → Resend; Python worker fallback only,
not a concurrent delivery path. **Alternative:** paid/always-on worker proposal was superseded.
**Trade-off:** asynchronous delivery and duplicated Python/Edge rendering contracts need retry
and parity tests. **Consequence:** API success is not immediate inbox delivery; Edge source
updates require their own deployment evidence. Evidence: `7a48941`, `bdd105a`,
[worker runbook](../../operations/supabase-email-worker.md),
[latest parity release](../../operations/email-template-redesign-production-2026-10-17.md).

## ADR-05 — Render Free initial-production API (accepted Oct 4 onward)

**Context:** free-tier deployment with HTTP/WSS and recovery requirements.
**Decision:** Vercel frontend, Render Free API, separate Supabase Production and exclusive
Production Redis. **Alternative:** Cloud Run was investigated and dropped; no completed
Cloud Run Production migration is proven. **Trade-off:** cold-start/capacity risks accepted
for initial rollout. **Consequence:** preserve rollback/health evidence and environment isolation.
Evidence: [Cloud Run audit](../../operations/cloud-run-backend-audit-2026-10-04.md),
[Render decision](../../operations/render-free-production.md).

## ADR-06 — One Event source, derived slider (accepted Oct 9; evolved Oct 14)

**Context:** duplicating Event and Slider records creates synchronization/ownership problems.
**Decision:** canonical Events, ready owned covers and deterministic query; no standalone
Slider table/editor/manual ordering. Client first-five rule differs from server cap 12.
**Trade-off:** editors manage Event eligibility, not separate promotion order. **Consequence:**
Landing and User Events share projection/cache/selector. Later optional schedule supports
announcements; Audience input/filtering was removed, retaining legacy stored values without a
data rewrite. **Historical alternative:** PUBLIC-only visibility filtering is superseded.
Evidence: [Event task](../../implementation/tasks/EVENT-AUDIENCE-SLIDER-001.md),
[slider code](../../../apps/api/app/services/event_sliders.py),
[User parity](../../implementation/tasks/FE-USER-EVENTS-001.md).

## ADR-07 — Independent strict build-time Event controls (accepted Oct 11)

**Context:** the shared switch coupled content administration to public launch.
**Decision:** strict independent Admin/public flags across routes, navigation and metrics;
ignore the former shared key. **Alternative:** direct Admin URLs while list/navigation were
hidden was not a supported rollout. **Trade-off:** two build inputs and consistent gating
require tests. **Consequence:** flags control presentation/release; backend ADMIN authority
remains mandatory. Evidence: [EVENT-FLAG-SPLIT](../../implementation/tasks/EVENT-FLAG-SPLIT.md),
[config](../../../apps/web/src/config/launch-scope.ts).

## ADR-08 — Isolated local acceptance before controlled Event rollout (accepted Oct 9)

**Context:** the sole Upstash Free database is Production-only; cloud staging cannot borrow it.
**Decision:** isolated local A–E acceptance, rollback-gated Production preflight, flag-OFF
release and safe smoke; later writes/activation separately authorized. **Alternative:** old
cloud-staging prerequisite superseded by explicit owner decision. **Trade-off:** provider
parity has explicit evidence limits, while security and regression gates remain.
Evidence: [local](../../operations/accept-event-001-local-acceptance-2026-10-10.md),
[release](../../operations/accept-event-001-production-release-2026-10-10.md).

## ADR-09 — Recovery cannot overwrite a newly started cohort (accepted)

**Context:** restoring old data after a new USER registers could destroy new-cohort truth.
**Decision:** monotonic registration marker permanently blocks that restore; reauth, phrase,
write barrier and verified database/avatar backup guard destructive execution. **Trade-off:**
more conservative recovery and additional operational ownership. **Consequence:** deleting the
new USER does not reopen restore. Production backup failure still blocks operational closure.
Evidence: SEM tasks, [reconciliation](../../operations/accept-001-reconciliation-2026-10-04.md),
[Production status](../../implementation/production-status.md). The disable-reset branch is
not an accepted change to current main.
