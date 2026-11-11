# FE-DASHBOARD-EVENT-PREVIEW-001 — Isolated square-preview release

Status: LOCAL VERIFIED / OWNER AUTHORIZES PRODUCTION RELEASE, 2026-11-11.

Approved source: bf823e96b569d9b6772cb50a7a055829936915ab.
Release baseline: f1d837be188eee878c013662c506e333ab5ce911.
Branch: release/user-events-preview-1x1-20261111.

Apply only the two image classes in apps/web/src/pages/user/user-events-page.tsx.
Preserve current eligibility, actions, navigation, aria-labels, locales and responsive grid.
No original-branch merge/cherry-pick, backend/API/database/config/Storage changes.

41 focused tests, TypeScript/build, affected lint/format and eight exact viewport/language
browser cases PASS. Portrait and square synthetic images remain square with centered cover;
equal same-row heights/action bottoms, no horizontal overflow at 1440/768/390/320px.
Owner accepted original UI 3/3; candidate rendered with current theme/component.
Authenticated Production acceptance remains UNVERIFIED until directly observed.

[Release evidence](../../project-knowledge/frontend/EVENT_PREVIEW_RELEASE_2026-11-11.md).
