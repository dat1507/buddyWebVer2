# ADMIN-DASHBOARD-RESTRUCTURE-001 - Admin operational statistics

Status: IMPLEMENTED LOCALLY - browser acceptance open, 2026-11-06.
Owner Task02B contract supersedes proposed five-KPI Overview. Local-only authorization.
Base b63655f4c3c65b7405a355079ceeba9cc51296c9 from freshly fetched origin/main,
including released Admin navigation and label fixes. Branch codex/admin-dashboard-restructure-stats.

Overview page, exclusive tests/translations and navigation removed. Users is default. /admin,
/admin/dashboard and retired announcements/campus/analytics each replace directly to /admin/users
inside unchanged RoleGuard. Existing public/login source kept. Events feature gating retained.
Seven links when Events ON, six OFF. Existing nested Event/Recap routes retained.

GET /api/admin/users/stats returns total_users and observed_at. One COUNT over User WHERE role=USER
AND deleted_at IS NULL, without profile/semester/activity/verification/search filters or joins.
GET /api/admin/events/stats returns published_events, upcoming_events, observed_at. One aggregate
statement counts PUBLISHED, published_at present, deleted_at null, with upcoming FILTER start_date
strictly greater than the same timezone-aware server observation. Visibility/Slider limits ignored.
Both endpoints use existing require_admin and private/no-store patterns, before dynamic ID routes.
Aggregate polling performs no writes or personal-data transfers. No migration or dependency added.

Users gets compact statistics above table. Events adds third Statistics tab, two cards, manual
Refresh, server observation time, initial/error/zero/stale displays. EN/DE localized. Existing
Matching aggregates unchanged, with cached values retained when a background refresh fails.
React Query private stats keys use 60000ms intervals, background polling disabled, staleTime0,
focus revalidation, refetch-on-mount and AbortSignal. Shared stats hook config reused by Matching.
ADMIN authenticated enabled gate stops polling on logout; existing private-cache cleanup retained.
Queries deduplicate requests; manual refetch uses cancelRefetch:false. Table queries have no interval.

Verification evidence is recorded in validation.md after final run. Real browser responsive/overflow,
console and full PostgreSQL application acceptance are UNVERIFIED. SQL predicate/count tests use
isolated in-memory SQLite, and API guards use ASGI mocks with existing auth fixtures. Fake timers
verify stats interval, hidden pause, focus resume, logout and cleanup. Navigation/auth tests mock
Users content to isolate router/session behavior; Users page has its separate table tests.
Local build keeps its existing large-chunk advisory.

Local review from this isolated worktree (existing local API credentials/config required):
1. apps/api: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
2. apps/web PowerShell: $env:VITE_API_URL='http://127.0.0.1:8000/api';
   $env:VITE_ADMIN_EVENTS_ENABLED='true'; npm run dev -- --host 127.0.0.1 --port 5199
3. http://127.0.0.1:5199/admin/users - existing local Admin login required.
4. Check Users count while searching/paging, Matching stats and unchanged participant query,
   /admin/events/statistics cards/Refresh/timestamp, EN/DE and 390px/desktop. Test /admin/dashboard
   and all three removed URLs, browser history and hidden-tab/visible refresh. Use local data only.

Commit reference: single local implementation commit containing this task record. Resolve with
 git log -1 --format=%H codex/admin-dashboard-restructure-stats. Exact SHA in final report.
Original main/worktrees/unpublished work preserved. No push, merge or deployment executed.

## Changed implementation paths

- apps/api/app/api/admin_events.py
- apps/api/app/api/admin_users.py
- apps/api/app/schemas/admin_statistics.py
- apps/api/app/services/admin_statistics.py
- apps/api/tests/test_admin_statistics.py
- apps/web/src/App.tsx
- apps/web/src/components/layout/admin-layout-integration.test.tsx
- apps/web/src/components/layout/admin-layout.test.tsx
- apps/web/src/components/layout/admin-sidebar-integration.test.tsx
- apps/web/src/components/layout/admin-sidebar-navigation.test.tsx
- apps/web/src/components/ui/admin-statistics.tsx
- apps/web/src/config/event-feature-flags.integration.test.tsx
- apps/web/src/features/admin-matching/queries/use-admin-matching.ts
- apps/web/src/features/admin-statistics.test.tsx
- apps/web/src/features/admin-statistics.ts
- apps/web/src/features/auth/admin-login-flow.test.tsx
- apps/web/src/features/auth/protected-route-integration.test.tsx
- apps/web/src/features/auth/user-login-flow.test.tsx
- apps/web/src/features/recaps/admin-events-tabs.tsx
- apps/web/src/locales/de/common.json
- apps/web/src/locales/en/common.json
- apps/web/src/pages/admin/admin-event-statistics-page.test.tsx
- apps/web/src/pages/admin/admin-event-statistics-page.tsx
- apps/web/src/pages/admin/admin-matching-page.test.tsx
- apps/web/src/pages/admin/admin-matching-page.tsx
- apps/web/src/pages/admin/admin-overview-integration.test.tsx
- apps/web/src/pages/admin/admin-overview-page.test.tsx
- apps/web/src/pages/admin/admin-overview-page.tsx
- apps/web/src/pages/admin/admin-users-page.test.tsx
- apps/web/src/pages/admin/admin-users-page.tsx
- apps/web/src/routes/admin-routes.ts
