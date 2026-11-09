# ADMIN-VIETNAMESE-TET-THEME-001 - Elegant Spring Celebration

Status: LOCAL VERIFIED / OWNER VISUAL ACCEPTANCE OPEN, 2026-11-09.
Branch: codex/vietnamese-tet-theme.
Base: remote main and approved Production 55e82608e884be705eeef82529feff82c341538d.
Owner closed Summer in separate local documentation commit
39d294664ac67688de0f9ee7135acac839e60e72. Existing unpublished history was preserved.

Add a fifth preset through the existing registry, Admin Settings, local preview,
public read and Admin publish endpoints. Preserve the campus Hero composition,
other presets and Admin shell. Keep the original access controls and audit transaction.
Production requires the forward-only 0027_site_theme_tet migration after 0026,
then compatible API and frontend deployments under separate authorization.
The migration replaces only the named CHECK constraint and preserves the stored row.

Focused source: apps/web/src/features/site-theme, EN/DE common locale catalogs,
apps/api/app/api/site_theme.py and apps/api/alembic/versions/0027_site_theme_tet.py.
Focused tests: frontend site-theme, landing-motion, landing-page; backend
test_site_theme_live, test_migrations and migration-head Recap cases.

[Design, verification, and owner review](../../project-knowledge/frontend/VIETNAMESE_TET_2026-11-09.md).
Local implementation, disposable test database and local commit only.
