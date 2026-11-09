# Vietnamese Tết - Elegant Spring Celebration

Task ADMIN-VIETNAMESE-TET-THEME-001. Local candidate, 2026-11-09.
Base 55e82608e884be705eeef82529feff82c341538d, verified against remote main and
the Production Vercel alias. Summer owner closure is documented separately.

## Design and implementation

Ivory and cream surfaces, festive red actions, dark warm ink, gold details, peach
pink, apricot yellow and restrained leaf green. Georgia and Segoe UI with serif
and sans-serif fallbacks use installed fonts, with no new font download. The EN/DE
preset names retain the Vietnamese diacritics in Tết.

The original campus photo and CTA composition frame original five-petal hoa mai
and hoa đào on separate branches. Two red bao lì xì have gold seams and ornament.
Twelve deterministic petal positions, mixed sizes, colors, delays and drift yield
gentle fall. Mobile draws six petals. One envelope sways. Motion is CSS-only and
clipped to the existing photo frame. The existing Pause control freezes motion.
Reduced motion and the Admin sample are static. The SVG is hidden from assistive
technology and ignores pointer input. Shared seasonal tokens give functional
pages a restrained treatment without adding illustration layers.

The existing preset registry drives the fifth Admin card, Preview and local
preview override. The existing API Literal gains tet. PostgreSQL migration
0027_site_theme_tet follows 0026_site_theme and widens the named CHECK constraint
without updating data. Its single ALTER statement preserves the singleton,
Default seed, RLS policies and grants. Public read, Admin authorization, CSRF,
publish locking and audit writes reuse the existing paths.

## Local evidence

- 23 frontend tests across three suites. TypeScript, affected ESLint, Prettier and
  Vite build passed. The existing bundle size advisory remains.
- 11 backend theme/migration tests passed with real disposable PostgreSQL 17.
  Upgrade from 0026 preserved the existing Summer row. Real API tests exercised
  publish, restore, public read, Admin authorization, CSRF, invalid input,
  duplicate-publish no-op and ordered audit values. Two additional Recap migration-
  head checks passed on a separate disposable database. Targeted Ruff lint and
  formatting passed.
- SQL inspection confirmed revision 0027_site_theme_tet, the five-value CHECK,
  RLS and all three existing policies. Runtime SELECT/UPDATE allowed and DELETE
  denied. A direct invalid-ID update failed at the CHECK constraint.
- Chromium passed EN/DE Landing at 1440, 390 and 320 px with the campus photo
  present, no horizontal overflow, and mobile menu and CTA usable. Petals move
  and freeze on Pause, envelope pauses, reduced motion is static, and mobile
  renders half the petals. Ten semantic text pairs measured at least 7.22:1.
- Eight controlled Hero comparisons for Default, Halloween, Christmas and Summer
  matched pixel-for-pixel at 1440 and 390 px with reduced motion, photo and launcher
  masking, and equivalent API interception. Prior scene implementations remain.
- Local Login/Register, synthetic signed-in Dashboard and chatbot panel rendered.
  Real synthetic Admin showed five presets and EN/DE Tết labels. Preview remained
  local and sent zero PUT requests. A separate disposable browser Publish/Restore
  issued two PUT requests, recorded Default to Tết to Default in the audit log
  and left Default stored. No Production account or database participated.
- Physical devices, alternate browser engines, and full Matching, Invitations,
  Conversations, Events and chatbot answer workflows were outside focused checks.

## Owner review

- [Tết Landing](http://127.0.0.1:5242/?theme-preview=tet)
- [Tết Login](http://127.0.0.1:5242/login?theme-preview=tet)
- [Tết Register](http://127.0.0.1:5242/register?theme-preview=tet)
- [User Dashboard](http://127.0.0.1:5242/user/dashboard?theme-preview=tet), then open the chatbot.
- [Admin Settings](http://127.0.0.1:5242/admin/settings), select Tết in Theme presets.

Use the local synthetic accounts defined in
[the review script](../../../apps/api/scripts/seasonal-theme-review.py). Use separate
browser profiles for User and Admin, or sign out of one before testing the other.
Check English and German, desktop and mobile, Pause/Resume and system reduced motion.
The stored local theme can be checked with /api/public/site-theme. Select a preset
without confirming Publish to review the Admin preview safely.

The local frontend listens on 5242 and API on 5243. The isolated PostgreSQL cluster
binds only to 127.0.0.1:55473, with its data under .local/tet-pg. The adapted local API
launcher is .local/tet-review-api.py. The Vite process uses VITE_API_URL=/api,
LOCAL_API_PROXY_TARGET=http://127.0.0.1:5243, VITE_SEASONAL_PREVIEW=true and
VITE_CHATBOT_ENABLED=true. No local Redis is required for these theme smoke checks.
Captures under .local/review: tet-1440.png, tet-390.png, tet-motion.gif, dashboard.png,
chatbot.png, admin-preview.png and admin-preview-de.png.

## Future release dependency

Obtain separate release approval. Verify recovery readiness and apply 0027 before
an API accepts or stores tet. Deploy the compatible API before making Publish
available in the new frontend. An older API cannot deserialize a stored tet value.
Any later application rollback to that API must first ensure an earlier preset
through the authorized workflow. The migration is forward-only. Keep the published
Production theme under the owner's control.
