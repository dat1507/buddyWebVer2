# Cloud Run backend audit — 2026-10-04

> **SUPERSEDED — 2026-10-04:** Cloud Run has been dropped by owner decision. Do not enable Google
> Cloud billing, create a Cloud Run service/load balancer, or continue its disposable test. Render
> Free is selected for the initial production rollout; the current architecture and release gates
> are documented in [Render Free initial-production runbook](render-free-production.md). The content
> below is retained only as the historical audit record and is not an active recommendation.

## Decision

Cloud Run can run the existing FastAPI container and its HTTP/WebSocket traffic, but it is only a
**conditional technical fit** and is **not approved for production deployment yet**.

Two project-specific facts prevent a near-zero-cost production recommendation today:

1. Every verified USER opens a global unread-notification WebSocket for the entire authenticated
   browser session, even outside chat, while also polling every 15 seconds. Cloud Run treats the
   whole WebSocket lifetime as an active request, so at least one instance remains billable while
   any socket is connected.
2. The application needs `api.vgubuddyprogram.com` (or another same-site first-party API name) for
   its host-only Secure, HttpOnly, SameSite=Lax cookies. Cloud Run's `run.app` hostname is
   cross-site with `www.vgubuddyprogram.com`. Direct Cloud Run domain mapping supports Singapore
   but is Preview and Google does not recommend it for production; Google's recommended global
   external Application Load Balancer adds a fixed cost that defeats the near-zero-cost goal.

A disposable Cloud Run test remains useful after the owner explicitly attaches an active billing
account. No Google Cloud resource, billing link, DNS record, or production deployment was created
during this audit.

## Source/config compatibility

| Concern | Current project | Cloud Run result |
| --- | --- | --- |
| Container | Pinned Python 3.12 amd64-compatible base, locked dependencies, non-root UID | Compatible |
| Listener | Uvicorn listens on `0.0.0.0:8000` | Compatible when Cloud Run container port is explicitly 8000 |
| HTTP/TLS | Cloud Run terminates TLS and forwards HTTP to the container | Compatible with secure cookies because cookie security is configured explicitly |
| Browser origin | Exact credentialed CORS/CSRF allowlist | Compatible after setting only the exact production frontend origin |
| Cookies | Host-only `__Host-` cookies, Secure, HttpOnly, SameSite=Lax | Requires a first-party API subdomain; `run.app` is not a browser-production substitute |
| WebSockets | Origin validation, reconnect/backoff, REST reconciliation | Compatible; Cloud Run forces reconnect at request timeout, maximum 60 minutes |
| Multi-instance WSS | Upstash Redis Pub/Sub | Compatible if production uses TLS `rediss://` and an isolated prefix |
| PostgreSQL | Async TLS; transaction-pooler support disables prepared statement cache | Compatible with Supabase; no static egress IP is needed unless allowlisting is introduced |
| Storage/email | Outbound HTTPS to Supabase Storage and Resend/Supabase worker | Compatible; outbound traffic contributes to egress |
| Health | Liveness and dependency-aware readiness endpoints | Use `/api/health/live` for a liveness probe; monitor `/api/health/ready` externally |
| Logs | Structured sanitized events to stdout/stderr | Collected by Cloud Logging without an application logging agent |
| Image/rollback | Pinned base plus lock file | Build one immutable Artifact Registry image; Cloud Run revisions support traffic rollback |

The Dockerfile does not need to change merely to consume `$PORT`: Cloud Run supports an explicitly
configured container port of 8000 and injects `PORT=8000`. Changing to a shell entrypoint would
reduce the current exec-form signal handling. The actual disposable test must prove that the
configured port and shutdown path behave as expected.

The unresolved proxy boundary is a separate acceptance gate. Uvicorn currently trusts forwarded
headers only from loopback. A Cloud Run test must record the observed transport peer and rate-limit
behavior. Do not switch to `--forwarded-allow-ips=*` or guess a peer CIDR. Until this passes, many
users could be collapsed onto one proxy address and share rate-limit buckets.

## Recommended Cloud Run shape for a disposable test

- Region: `asia-southeast1` (Singapore, Tier 1 pricing).
- Execution/billing: request-based, CPU throttled outside requests, minimum instances 0.
- Instance: 1 vCPU, 512 MiB; do not use sub-1-vCPU mode because it forces concurrency 1 and is a
  poor WebSocket fit.
- Concurrency: start at 80; maximum instances 1 for the cost-bounded disposable test. Production
  sizing would need measured concurrency before allowing 2 or more instances.
- Request timeout: 3600 seconds. Clients already reconnect and recover authoritative state.
- Ingress: public HTTPS is required for browser/API traffic; authorization remains in FastAPI.
- Container port: 8000.
- Secrets: Secret Manager references for credentials; plain environment variables only for
  non-secret configuration. Keep migration and DR credentials out of the service entirely.
- Health: liveness path `/api/health/live`; use `/api/health/ready` as a post-deploy gate.
- Image: Artifact Registry with deletion/retention policy; do not enable paid vulnerability
  scanning without approval.
- Custom domain: none during the disposable test. Use HTTP clients for cookie flows and an explicit
  Origin for WSS. A browser end-to-end cutover waits for a separately approved domain design.

The service needs only `DATABASE_URL`, not `DATABASE_MIGRATION_URL` or `DATABASE_BACKUP_URL`.
Migration and DR jobs stay local/operator-controlled. The runtime also needs its current auth,
CSRF, email-sealing, Redis, Storage, CORS, app-origin, and dedicated maintenance values. Secret
Manager's free allowance is six active versions; this application has more than six genuine
secrets, so a small Secret Manager charge is likely even when Cloud Run compute is free.

## Cost model for approximately 150 users

Google Cloud requires an active Cloud Billing account even when usage remains inside Free Tier.
Free Tier is an allowance, not a spend cap. Budgets alert but do not stop charges.

For request-based Cloud Run in a Tier 1 region, the checked prices are $0.000024/vCPU-second
($0.0864/vCPU-hour) and $0.0000025/GiB-second ($0.009/GiB-hour), after an account-wide monthly
allowance of 180,000 vCPU-seconds, 360,000 GiB-seconds, and two million requests. At 1 vCPU and
512 MiB:

| Monthly active instance time | Approximate compute | Interpretation |
| --- | ---: | --- |
| Up to 50 instance-hours | $0 | Inside CPU and memory allowance, before egress/secrets |
| 120 instance-hours | ~$6.05 | 70 CPU-hours over free; memory remains inside its allowance |
| One instance continuously active (~720 h) | ~$60.23 | ~$57.89 CPU + ~$2.34 memory |

These are active **instance-hours**, not user-hours. Up to the configured concurrency can share an
instance, while multiple active instances multiply the cost. The current global WebSocket means a
single signed-in tab can keep an instance active. With 150 users, actual cost cannot be inferred
from account count alone:

- short, clustered login/chat sessions may remain around $0–$3/month;
- several active hours every day plausibly reach $5–$15/month;
- continuous sockets approach ~$60/month per continuously active instance.

Internet egress, Artifact Registry above 0.5 GiB, Cloud Logging above allowance, Secret Manager
above six active versions, tax, and any load balancer are additional. Singapore outbound traffic
does not receive the North America-only 1 GiB internet egress allowance. Static outbound IP would
require VPC/NAT and extra cost; the current external providers do not justify it.

The minimal cost fix before production is to remove or feature-gate the always-on global unread
WebSocket and retain the existing 15-second authoritative polling, while keeping the conversation
WebSocket only while a chat view is open. Measure that version before choosing a platform. This
change is not part of the current audit patch.

## Render Starter comparison

| Dimension | Cloud Run candidate | Render Starter |
| --- | --- | --- |
| Base compute | Usage-based; can be $0, but global sockets can make it much higher | Predictable $7/month for 0.5 CPU/512 MiB |
| Billing prerequisite | Active Google Cloud Billing account required | Existing Render account/service |
| Cold start | Yes at min 0 | Always-on paid instance |
| WebSocket duration | Maximum request timeout 60 minutes, then reconnect | No fixed Render WebSocket timeout; reconnect still required on deploy/restart |
| Stable custom domain/TLS | Direct mapping is Preview; recommended LB costs extra | Mature managed custom domain/TLS included |
| Current project setup | New project/IAM/secrets/image/logging/domain workflow | Existing deployed Docker workflow and domain behavior |
| Cost predictability | Low until WebSocket-hours are measured | High at $7 plus any overage |
| Rollback | Immutable revisions/traffic switching | Instant rollback and zero-downtime deploy support |

For this application as written, Render Starter is the lower-risk production choice despite the
fixed $7. Cloud Run becomes compelling only after the global socket is removed/gated and a
production-grade same-site domain path is accepted without an expensive load balancer.

## Test and cutover gates

After explicit billing authorization, a disposable test may validate only the default `run.app`
service and must set min instances 0, max instances 1, a short retention policy, and a budget alert.
It must prove:

1. image build, non-root startup, port 8000, SIGTERM shutdown, liveness and dependency readiness;
2. HTTP auth using an HTTP cookie jar, exact CORS/CSRF rejection, and no credential leakage;
3. trusted and untrusted WSS Origin behavior, 60-minute reconnect, Redis Pub/Sub, and REST recovery;
4. observed proxy peer/rate-limit identity under concurrency;
5. cold-start latency and at least one scale-to-zero/wake cycle;
6. Cloud Logging sanitization, revision rollback, and deletion of every disposable resource.

Production additionally requires a measured WebSocket-hour report, two-instance test if needed,
same-site custom-domain decision, DNS/TLS acceptance, offsite DR rehearsal, scheduler acceptance,
and completion of the remaining ACCEPT-001 evidence. No production database or DNS change belongs
in the disposable test.

## Primary references

- [Cloud Run container contract](https://docs.cloud.google.com/run/docs/container-contract)
- [Cloud Run WebSockets](https://docs.cloud.google.com/run/docs/triggering/websockets)
- [Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Cloud Run request timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout)
- [Cloud Run minimum instances](https://docs.cloud.google.com/run/docs/configuring/min-instances)
- [Cloud Run CPU configuration](https://docs.cloud.google.com/run/docs/configuring/services/cpu)
- [Cloud Run custom domains](https://docs.cloud.google.com/run/docs/mapping-custom-domains)
- [Google Cloud Billing requirement](https://docs.cloud.google.com/docs/get-started/learn-about-billing)
- [Secret Manager pricing](https://cloud.google.com/secret-manager/pricing)
- [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing)
- [Render pricing](https://render.com/pricing)
- [Render WebSockets](https://render.com/docs/websocket)
- [Render custom domains](https://render.com/docs/custom-domains)
