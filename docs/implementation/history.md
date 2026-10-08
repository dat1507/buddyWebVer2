# Important implementation history

This file preserves the milestones future agents need without replaying completed session logs.

## Completed foundations

- Frontend foundation, migrated landing UI, EN/DE localization, accessible navigation and auth entry
  were completed before the backend vertical slice.
- FastAPI/SQLAlchemy/Alembic, credentialed CORS, User/RBAC, password/JWT/CSRF services, public auth,
  refresh/logout/current-session, rate limiting, admin seed and guarded frontend routes were
  completed and accepted.
- Profile models/catalogs/migrations, private avatar lifecycle, profile completion/eligibility,
  onboarding/edit/view/dashboard and Admin profile reads were completed.
- Audit and shared private Storage foundations were completed.

## Buddy Matching V2 milestones

- Email verification/outbox, capability guard, custom preferences and deterministic recommendations
  completed in September 2026.
- Invitation persistence/APIs/UI/email, ACTIVE multi-Buddy Match, type lock, Current Buddies and chat
  completed by 2026-10-01.
- Admin monitoring-only APIs/UI and Semester backup/reset/restore safety completed by 2026-10-02.
- `ADMIN-012` user list and `ADMIN-013` user detail were completed and staging-accepted on
  2026-10-03/04.

## Operations and acceptance

- Staging Edge/Cron email delivery and OPS observability/recovery runbooks passed.
- The maintenance scheduler passed staging acceptance on 2026-10-04.
- Reset/restore reconciliation progressed through successful guarded reset/restore and the final
  restore-blocked-after-new-USER scenario, which closed on 2026-10-07.
- Full `ACCEPT-001` stayed open for residual evidence, later reclassified as post-deployment
  hardening for the smaller reporting MVP rather than falsely marked complete.

## Production

- Render Free was selected for the initial API with known cold-start/capacity risks accepted.
- On 2026-10-07, Production Upstash reallocation, Supabase bootstrap, runtime role and Alembic head
  `0021_restore_runtime_permissions` were verified.
- The missing Production email runtime was diagnosed and configured on 2026-10-08. Expired rows
  failed safely; a fresh verification email was delivered and consumed normally.
- One Admin account was created via the trusted CLI. The last operator record still lacked Admin UI
  smoke and a second designated USER for full Buddy lifecycle smoke.
- Direct checks on 2026-10-08 confirmed first-party DNS, public live/readiness, frontend API target,
  anonymous auth boundary and CORS behavior.

## Event scope

- The current launch uses a static project-owned Upcoming Events carousel.
- A later commit `81979ce` changed the carousel to five current posters and centered titles.
- The canonical dynamic Event/Admin Event lane remains deferred; it must follow the exact Part 27
  chain and cannot inherit completion from the static carousel.
