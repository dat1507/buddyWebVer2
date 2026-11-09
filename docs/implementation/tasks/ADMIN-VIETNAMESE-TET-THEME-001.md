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


## Navbar refinement - 2026-11-09

Owner requested the Tết-only sticky Navbar fireworks strip before local acceptance.
Implemented decorative ray clusters and sparkles with existing Landing pause and
static reduced motion. The four scroll effects are evaluated in Project Knowledge
and await separate approval. Frontend-only verification passed (40 focused tests).
Previous implementation commit d87ec0d860571bbcba776281d7df23a84061012a is retained.

## Approved Landing scroll effects - 2026-11-09

Owner approved A and D. Explore More and About have sparse edge petals and a
one-time golden sparkle at each section entrance. Desktop and tablet use
gentle scroll drift. Phones show static petals. The existing Landing pause and
system reduced motion govern both effects. Frontend-only changes build on
6f2ed111668e1233ccbf7eb0fab2f63f49b4e2c5.

Focused source: the About and Explore More Landing sections and the Tết petal,
scene and section-effect modules in apps/web/src/features/site-theme.
Focused verification: About, Explore More, Landing motion and Landing assembly
suites, plus the browser review linked above. Local visual acceptance is open.
