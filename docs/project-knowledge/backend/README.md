# Backend implementation

[main.py](../../../apps/api/app/main.py) registers FastAPI routers, exact-origin credentialed
CORS, shared rate limiting, observability and safe exception handlers. Python domain
services use async SQLAlchemy sessions and asyncpg/PostgreSQL; Pydantic schemas validate
input/output contracts. [Backend README](../../../apps/api/README.md) retains installation
and configuration instructions.

## A request from boundary to persistence

1. Middleware handles observability, CORS and shared limits.
2. Router dependencies recover the current persisted identity, role, CSRF and capability.
3. Pydantic validates the request and the router invokes a focused service.
4. Services query/lock rows, enforce business rules and stage writes; the calling transaction
   boundary commits related domain/audit/outbox effects together.
5. Schemas return bounded data. Exceptions become sanitized status/reason responses.

Authentication proves who is calling; authorization decides whether that caller may perform
this operation. Capability checks add domain readiness such as verified email and profile
eligibility. A submitted UUID never grants ownership.

## Endpoint map

Paths below include `/api`; consult the linked router for exact methods, DTOs and errors.

| Area                 | Important routes                                                                                     | Source / authority                                                                                                                                                                       |
| -------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auth                 | `/auth/register`, `/login`, `/refresh`, `/logout`, `/me`, `/csrf`, `/csrf/session` under `/api/auth` | [auth.py](../../../apps/api/app/api/auth.py); cookie/CSRF/session dependencies                                                                                                           |
| Verification/email   | `/api/auth` verification and email-change operations                                                 | Same router; [token service](../../../apps/api/app/services/email_verification.py) and outbox                                                                                            |
| Profile              | `/api/profile`, completion, catalog and photo operations                                             | [profile.py](../../../apps/api/app/api/profile.py), [catalogs](../../../apps/api/app/api/profile_catalogs.py), [photos](../../../apps/api/app/api/profile_photos.py); own-user authority |
| Recommendations      | `/api/matching/recommendations`                                                                      | [matching.py](../../../apps/api/app/api/matching.py); verified eligible USER                                                                                                             |
| Invitations          | `/api/matching/invitations`, incoming/sent, UUID accept/decline/cancel/hide                          | Same router; recipient/sender action rules                                                                                                                                               |
| Buddies              | `/api/matching/buddies`                                                                              | Same router; authoritative current relationships                                                                                                                                         |
| Chat HTTP            | `/api/chat/conversations/{id}/messages`, `/messages/read`, `/api/chat/unread-summary`                | [chat.py](../../../apps/api/app/api/chat.py); participant authorization                                                                                                                  |
| Chat WSS             | `/api/ws/chat/notifications`, `/api/ws/chat/{conversation_id}`                                       | [chat_realtime.py](../../../apps/api/app/api/chat_realtime.py); authenticated origin/session/member checks                                                                               |
| Public Events        | `/api/events`, Event detail and `/api/event-sliders`                                                 | [events.py](../../../apps/api/app/api/events.py), [slider](../../../apps/api/app/api/event_sliders.py); publication/deletion rules                                                       |
| Admin Events         | `/api/admin/events` lifecycle/editor/media operations                                                | [admin_events.py](../../../apps/api/app/api/admin_events.py), [media](../../../apps/api/app/api/event_media.py); ADMIN, CSRF, expected version                                           |
| Admin users/matching | `/api/admin/users`, `/api/admin/matching`                                                            | [users](../../../apps/api/app/api/admin_users.py), [monitoring](../../../apps/api/app/api/admin_matching.py); bounded monitoring reads                                                   |
| Semester             | `/api/admin/semesters/management`, reset/restore prepare/preflight/execute                           | [admin_semesters.py](../../../apps/api/app/api/admin_semesters.py); guarded destructive workflow                                                                                         |
| Maintenance/health   | `/api/internal/maintenance`, `/api/health/live`, `/api/health/ready`                                 | [maintenance](../../../apps/api/app/api/maintenance.py), [health](../../../apps/api/app/api/health.py); scheduler auth versus public diagnostics                                         |

## Service responsibilities

Eligibility, scoring and ranked projection are separate Matching services. Invitation sending,
expiry, reads, acceptance and owner mutations are separate state-machine concerns. Buddy
activation and conversation creation preserve one unordered ACTIVE pair and one conversation
per Match. Chat REST persists/reconstructs history while realtime transports events.

Event lifecycle mutations, public queries, Admin queries, slider projection and media lifecycle
are separate modules. This avoids using an Admin response as a public DTO. Public detail/list can
retain published CANCELLED Events; the slider excludes cancellation and requires ready covers.

Database backup, avatar backup, verification, management, reset and restore are separate Semester
services because recovery has different privilege, consistency and failure boundaries from
ordinary profile edits. Their presence does not close Production backup acceptance.

Request validation errors return only type/location/message fields. Configuration failures
return sanitized 503 responses. CSRF errors use a generic 403. Private responses and auth
errors use no-store policies where defined. Review exact route behavior rather than assuming
every 404, 409 or 503 means the same failure.

See [workflow details](../WORKFLOWS.md), [security](../security/README.md) and
[database integrity](../database/README.md) for the business rules behind these boundaries.
