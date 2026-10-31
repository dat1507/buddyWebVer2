# OPS-ALEMBIC-VERSION-LENGTH-001 — Safe fresh-install revision capacity

Status READY — FOLLOW-UP / NOT ASSIGNED. Owner requested separate follow-up2026-10-31.
Existing0022_public_event_visibility_default revision is36 characters; Alembic's default version
column is VARCHAR32. Recovered unmodified fresh migration FAIL is preserved; fixture-only widening
allowed integration and is not a clean-install PASS. Application runtime/Docker startup do not run
migrations; this frontend-only release adds none and retains deployed API/migration bytes.
Design a safe bootstrap/version-table solution, preserving published revision IDs/applied history,
then verify fresh upgrade, upgrade of representative existing schemas, graph/heads and least-privilege
boundaries in disposable databases. No Production schema/business-rule change is authorized here.
Scoped release exception expires if backend/schema changes, migration execution or fresh database
provisioning become part of the UI release. No implementation is assigned now.
