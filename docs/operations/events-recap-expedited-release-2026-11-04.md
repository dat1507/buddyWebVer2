# Events Recap expedited controlled release — 2026-11-04

IN PROGRESS. Owner explicitly accepts missing pre-release backup and defers complete PostgreSQL+
Storage capture for this release only. No complete verified backup exists; post-release backup
cannot recover exact pre-release state; migration/corruption may cause irreversible loss. Existing
synthetic restore does not prove actual recovery. Backup/recovery readiness NOT PASS.
[OPS-PRODUCTION-BACKUP-001](../implementation/tasks/OPS-PRODUCTION-BACKUP-001.md):
DEFERRED — OWNER-ACCEPTED RISK. No backup/Hyper-V setup performed for this release.

## Minimal safety review and migration evidence

Approved9049f444515cad258905f0f18d04d9d13e18d431 clean/exactremote, main6d32d1a unchanged at review;
CI41774722426 PASS936frontend/1880backend/37existing skips reused. Migration source unchanged.
Actual Production0021/32char Alembic column/24app tables, Recap tables absent. UUID/audit column
contracts match. Required runner widens version column128;0022 only changes FUTURE Event visibility
default toPUBLIC;0023 creates3private Recap tables/FKs;0024adds first-publication/cleanup metadata.
No DROP/TRUNCATE/DELETE/UPDATE of existing user/Profile/Match/Conversation/Event rows. Rollback
is not a destructive downgrade. Old backend is compatible while newly added Recap tables are empty.
New backend handles linked Event deletion with explicit dependency conflict, not silent loss.

Exact offline forward SQL from approved Alembic files was wrapped in one atomic guarded DO with
revision/new-schema checks and before/after critical counts; synthetic-only transport check PASS:
0021->0024/width32->128, User/Event seed and existing Event visibility preserved; second execution
fails closed. No unnecessary full local suites. SQL SHA256:
cd038429b59ba344085e300ee0493276f32ed36051dd444f740da9148b64bbf9.

Owner-authorized Supabase migration applied successfully on the designated existing Production
project. Result0024_recap_retention; version capacity128; new4tables RLS-on; runtimeCRUD granted;
anon/authenticated/service_role have noSELECT. New Recap/photo/image/cleanup row counts all0.
Critical counts unchanged before/after:Users6,Profiles5,Matches3,Conversations3,Messages6,Events4.
These counts are diagnostics, NOT a data backup or proof of all row contents.

## Targets and backend-first source control

Render existing vgu-buddy-api-production/main/apps/api, AutoDeployOFF verified. Current pre-release
live deployc0687ba8e1253189bd297f60f2d8e8f24e44ecca retained as reference, not automatic rollback.
Vercel Production GitHub provider record7536457105 for6d32d1a has success byvercel[bot]; public
www.vgubuddyprogram.com HTTP200/Vercelheader. Code-split public assets use api.vgubuddyprogram.com;
DNS CNAME maps to confirmed Render Production service. No inferred target from wrong credentials.
Direct Vercel dashboard unavailable; provider status/public domain evidence retained explicitly.

Render MCP manual deploy takes latest main, no commit selector. To keep new frontend behind ready
backend, isolated backend staging commits only approved apps/api + CI (20files). Both trees match
9049f44 exactly; frontend tree matches originalmain6d32d1a exactly. No dependency/config/source
change outside approved backend. Local main/other branches/worktrees/unpublished work preserved.
Normal fast-forward main6d32d1a->a5aceb6e0d5033846d2980dd953ca6e607774939 succeeded. No force.
Frontend files unchanged; any provider frontend rebuild at this stage uses existing approved UI.
Next: stageCI, manual backend deploy/live+API checks, final source-identical frontend integration,
exact-SHA hostedCI on protected existing RC branch, then normal main promotion and Production checks.
No backend deploy triggered yet at this record. No new Recap writes or test account created.
