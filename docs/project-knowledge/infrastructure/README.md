# Infrastructure and delivery

The latest dated [Production status](../../implementation/production-status.md) is authoritative
for observations. Nothing in this audit queried a provider or accessed Production data.

## Environments and service ownership

| Environment              | Evidence-backed topology / limits                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| Local                    | Docker Compose PostgreSQL, Redis, API, fallback worker and web; isolated test dependencies                           |
| Historical staging       | Supabase/Storage/Edge/Cron acceptance and recovery records; staging API suspended during approved Redis reallocation |
| Production frontend      | Vercel, `www.vgubuddyprogram.com`, root `apps/web`                                                                   |
| Production API           | Separate Render Free Docker service, `api.vgubuddyprogram.com`, non-root Uvicorn                                     |
| Production durable state | Separate Supabase project, private PostgreSQL schema and Storage                                                     |
| Shared limits/realtime   | Upstash Redis reallocated exclusively to Production; no simultaneous staging sharing                                 |
| Transactional email      | Supabase Cron → email-worker Edge Function → Resend, using committed outbox intent                                   |
| Maintenance              | Supabase scheduled authenticated request to `/api/internal/maintenance`                                              |

Local configuration: [Compose](../../../docker-compose.yml),
[API Dockerfile](../../../apps/api/Dockerfile). Deployment semantics and recorded Free-tier
risks: [Render runbook](../../operations/render-free-production.md). Provider pricing/quotas
here are historical context, not current vendor advice; consult official provider terms before
future provisioning. There is no repository Render blueprint proving dashboard state.

## Evolution and decisions

The [Cloud Run audit](../../operations/cloud-run-backend-audit-2026-10-04.md) documents an
investigation. The selected initial-production API is Render Free; available evidence does not
establish that Production migrated from a live Cloud Run service. Report this as provider
selection/evaluation history rather than inventing a completed migration.

Paid/always-on mail-worker proposals were replaced with hosted Cron/Edge delivery. The Python
worker remains fallback and must not deliver concurrently with the hosted worker. Email templates
exist in both runtimes, so changes require parity checks and, when authorized, separate Edge
deployment. Latest [email release evidence](../../operations/email-template-redesign-production-2026-10-17.md)
records exact-source Vercel, Render and Edge acceptance.

The sole free Redis resource moved from staging to Production only after detaching consumers,
auditing an empty keyspace and rotating credentials. Isolated local Event acceptance later
replaced an unavailable cloud-staging dependency. That environment decision retained security
and quality gates, rather than permitting local tests against Production services.

## Configuration and release

`VITE_*` values are public build inputs bundled into the frontend. They cannot store secrets.
API signing/database/Storage/email credentials belong to server-side environment management.
Exact first-party origins preserve cookie and WSS security boundaries; a permissive CORS change
is not an acceptable substitute for correct domains.

Independent `VITE_ADMIN_EVENTS_ENABLED` and `VITE_PUBLIC_EVENTS_ENABLED` enable only for exact
`true`. Missing/invalid values fail closed; the former shared flag is ignored. Flag changes
require rebuilding the frontend; they are not live database toggles. See
[launch-scope.ts](../../../apps/web/src/config/launch-scope.ts).

Documented workflow uses current `main`, local validation, explicitly authorized push/deploy,
exact-SHA CI/provider confirmation and bounded smoke. This audit creates one local docs commit
only. Because push triggers CI and linked hosting, a documentation commit must not be pushed
as an incidental maintenance action.

## Monitoring and recovery

Liveness answers whether the API process is alive; readiness checks database, Redis and configured
email/Storage dependencies. Neither proves a successful backup or real email delivery.
Structured request IDs/logs and [observability](../../operations/ops-003-observability.md),
[recovery](../../operations/ops-003-recovery.md) and
[credential rotation](../../operations/ops-003-credential-rotation.md) runbooks provide operations
procedures. Their existence does not establish fresh alerts or a rehearsed Production restore.

Retained Vercel and Render rollback candidates were recorded after the Event release. The
private Semester backup failure, named decision/execution/recovery owners and accepted
post-repair hold remain blockers. Code rollback does not undo data mutations; whole-system DR
requires verified encrypted backups plus a disposable restore, still open under
[off-site DR](../../operations/supabase-free-offsite-dr.md).
