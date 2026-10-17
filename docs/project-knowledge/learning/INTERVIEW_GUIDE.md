# Evidence-grounded interview preparation

These are model explanations of repository behavior, not a claim that you personally made
every decision. Adapt them only to work you understand and can substantiate with a diff.

## 1. Explain your project architecture

“BuddyWebv2 has a React/TypeScript frontend and a FastAPI backend. The browser uses cookie-authenticated
HTTP requests for domain operations and authenticated WebSockets for realtime chat. PostgreSQL
stores private application state; Redis supports rate limiting and fanout. Supabase hosts the
database, private media and scheduled Edge workers. Vercel serves the frontend and Render runs
the API. FastAPI owns auth rather than Supabase Auth.”

Follow-up: draw [the architecture](../ARCHITECTURE.md) and identify which component owns truth
when a WebSocket disconnects.

## 2. Why this technology stack?

“The repository combines typed UI contracts, Python API validation and relational integrity.
React supports component reuse; TanStack Query handles server data; FastAPI/Pydantic define
request contracts; PostgreSQL supplies transactions/constraints; Alembic versions schema changes.
Recorded infrastructure decisions favor a cost-bounded initial deployment. The full original
comparison of framework alternatives is not documented, so I would not invent it.”

Evidence: [stack and boundaries](../frontend/README.md), [ADRs](../decisions/README.md).
Follow-up: discuss a trade-off you can demonstrate, such as maintaining Python/Edge email parity.

## 3. How does Buddy Matching work?

“It is deterministic recommendation, followed by consent. The API first checks verified,
complete, opted-in, current-semester opposite-type eligibility and excludes existing ACTIVE
pairs in both directions. It scores interests 40, activities 35, availability 15, language 5
and major 5. Set/time overlap and normalized equality produce explainable points. Exact
fractions determine ranking; display uses half-up rounding. Accepting an invitation later
creates the Match and conversation atomically.”

Follow-up: work the example in [Workflows](../WORKFLOWS.md). Missing signals score zero;
there is no renormalization, trained model or guaranteed single-Buddy assignment.

## 4. How do frontend and backend communicate?

“Feature hooks call typed clients through one HTTP wrapper. It includes browser cookies,
requires a CSRF header for mutations, supports abort/timeout and sanitizes errors. Response
parsers validate server data; query keys and invalidation keep related UI consistent.
Landing and User Events demonstrate reuse of one locale-keyed query and first-five selector.”

Evidence: [api.ts](../../../apps/web/src/lib/api.ts),
[shared Event query](../../../apps/web/src/features/events/queries/use-event-sliders.ts).

## 5. How is authentication secured?

“Passwords are hashed on the server. Access/refresh credentials use protected cookies;
frontend state holds sanitized identity in memory. Refresh rotation/reuse detection and
logout revocation are server-owned. Signed CSRF, exact-origin credentialed CORS and WSS
Origin checks address different boundaries. The backend rechecks persisted role and Buddy
capability; UI route guards are not the security authority.”

Follow-up: distinguish same-site from same-origin using [security](../security/README.md).
Do not show cookie/token values during an interview.

## 6. Why have both validation and database constraints?

“Validation gives useful errors, but two valid concurrent requests can still conflict.
Participant locks and rechecks control transitions; PostgreSQL foreign keys, checks and unique
indexes reject impossible final states. Canonical low/high user IDs make A→B and B→A one
ACTIVE pair. Expected versions stop stale Event/profile saves from overwriting newer edits.”

Follow-up: explain the acceptance race and why a partial unique index is stronger than checking
for an existing row once. See [database guide](../database/README.md).

## 7. What happens when an invitation is accepted?

“Only the intended recipient can accept an effective pending invitation. The service locks and
revalidates identity/eligibility/expiry, activates the relationship, gets or creates the Match's
conversation and stages email intent in one transaction. A duplicate ACTIVE unordered pair is
forbidden. Failure should not leave only half the domain state.”

Evidence: [acceptance implementation](../../../apps/api/app/services/invitation_acceptance.py).
Follow-up: explain why an external email provider should not run inside the database transaction.

## 8. How does chat recover from failure?

“PostgreSQL stores messages; WSS/Redis accelerates delivery. A client-generated retry identity
is scoped to the authenticated sender/conversation so retries do not duplicate messages.
After reconnect the client reconciles REST history and unread state. A connected socket by
itself does not prove history is complete.”

Evidence: [chat workflow](../WORKFLOWS.md) and [tests](../testing/README.md).
Follow-up: distinguish delivery notification, durable persistence and read status.

## 9. How was the application deployed?

“The recorded deployment uses first-party Vercel frontend and Render API domains, Supabase
durable/private services and exclusive Production Redis. Releases require exact-source CI,
provider/artifact confirmation, controlled flags and bounded smoke. Cloud Run was evaluated
and dropped; I cannot claim a completed Cloud Run Production migration. The latest recorded
email release includes Vercel, Render and Edge source parity.”

Follow-up: explain build-time flags and why code rollback does not restore mutated data.
Evidence: [infrastructure](../infrastructure/README.md).

## 10. Describe a challenging bug

Choose one you actually investigated. A documented example is the WSS regression harness:
fake Redis publication crossed event loops and teardown raced async cleanup. The fix used the
TestClient portal and deterministic socket/subscription shutdown; application WSS code was
unchanged. Explain evidence and validation rather than saying “upgrading Python fixed it”.

Another example is decode-safe Landing transitions. The failed Semester backup is still open;
do not present it as a solved incident. See [incident evidence](../incidents/README.md).

## 11. How did you test changes?

“The project combines pure-function/component tests, API/service tests, opt-in real-database
integration, static/type checks, migration/package validation, browser acceptance and exact-SHA
release smoke. Each proves a different boundary. Historical test counts are scoped to their
commit, and opt-in SKIP is not PASS. For a documentation-only change I validate links/evidence
and source isolation instead of repeating accepted runtime gates.”

Follow-up: choose one meaningful negative scenario from [the regression map](../testing/README.md).

## 12. What would you improve?

“First I would close documented operational gaps: private backup verification, recovery ownership
and encrypted disposable restore evidence. I would reconcile stale deployment labels and record
the missing Production migration revision. Then I would measure actual frontend bundle/runtime
behavior before optimizing, and preserve one canonical Event projection.”

These are proposed priorities, not completed work. Avoid arbitrary scaling claims without
traffic/latency data. See [open gaps](../DOCUMENTATION_AUDIT.md).

## Practice contribution story

Use: requirement → observed failure/constraint → exact diff → invariant → verification →
remaining limitation. Identify the commit and source function; explain one rejected approach
only if actually documented or personally known. Never claim users served, performance gains,
incident impact or independent authorship without evidence.
