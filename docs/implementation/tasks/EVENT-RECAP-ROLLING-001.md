# EVENT-RECAP-ROLLING-001 - Rolling10 and Facebook

DONE LOCAL - NEW HOSTED CI REQUIRED / PRODUCTION NO-GO. Owner2026-11-04 authorizes isolated local implementation/commits from approvedc742173
with currentorigin/main6d32d1a. Permanent automatic eviction, no archive/manual confirmation.
At most10published, original publicationtime/UUID tie, atomic/concurrent/retry-safe; durable private
media cleanup outside transaction with truthful pending/retry. Preserve linkedEvents/Slider/Profile.
Add Admin retained10 warning and eviction identity, public Facebook EN/DE section in approved style.
Focused tests then required integration checks; migration/rollout/recovery/cost/readiness docs.
No push/merge/deploy/Production operations; preserve dirty recovery worktree and all histories.
Focused paths: Recap API/services/models/schema/Alembic/tests, public/admin recap components/locales/
styles/tests, shared AdminEvent test reconciliation, existing Event Slider regressions and release records.
New exact-SHA hostedCI and separate Production approvals required. ProductionNO-GO.

## Completion evidence

[Report](../../project-knowledge/frontend/EVENT_RECAP_ROLLING10_2026-11-04.md),
[manifest](../../project-knowledge/frontend/EVENT_RECAP_ROLLING10_MANIFEST_2026-11-04.json).
Postgres advisory publication lock, first-publication/UUID ordering; hard Recap/photo/image metadata
deletion + durable private cleanup queue atomic with publication. Network deletes aftercommit,
partial failure/404 retry-safe, Event/profile/Slider protected. Drafts excluded; existing published
edit and stale/idempotent retries do not evict. Legacy>10 migration fails closed without deletion.
Fullfrontend936PASS, backend1879PASS/37existingSKIP; final27affected + final3upgrade/livePASS; strict
mypy330, lint/types/format/build/package/headPASS. Added EN/DE safeFacebook link and statusfeedback;
focused33+2PASS; real loopback/Pillow/localStorage7PASS. Final small migration/type/package checks
recorded in manifest; no unnecessary full-suite repeat after scoped hardening. UI visual review
UNVERIFIED because local browser disabled. Source runtime/locks/currentmain sharedpaths preserved.
Review5198/8044 newlocalDB only. PreviousRC and uncommitted recovery-prep untouched; no push/deploy.
Migration0024 and new hostedCI/owner changedUIreview/recovery/capacity/advisory/release authorization
required. Stop local task; backup recovery requirements not waived by retention model.
