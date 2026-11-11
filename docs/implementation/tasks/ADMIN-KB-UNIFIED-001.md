# ADMIN-KB-UNIFIED-001 — Unified FAQ management

Status: DONE — LOCAL VERIFIED on 2026-11-11. Owner local acceptance pending.
Assigned by the owner's pasted implementation contract; new scope supersedes the old Event handoff
only in this isolated worktree. Baseline deef12c; branch codex/admin-kb-unified.
Implementation commit: `6dec701e03ebf412b122fb9017523815de655839`.

Unified 28 packaged entries and managed identities, generic FAQ label, linked-row deduplication,
EN/DE question/alias/answer search, category/status filters and 20-row pagination, full read-only
details, prefilled replacement editing and pinned read-only guide link are complete.
An additive ADMIN/no-store catalog reads draft/public revisions in one SQL snapshot; existing
mutation endpoints, source restrictions, retrieval, fallback, flags and canonical guide bytes remain
unchanged. Existing nonverified entries remain excluded from publication/replacement; actionable
validation remains visible. No schema/config/provider change or Production operation.

250 backend regression/catalog tests + 1 real PostgreSQL lifecycle + 45 frontend tests PASS.
TypeScript, affected lint/format, Ruff/mypy and production build PASS; existing bundle advisory.
32 EN/DE browser cases at 1440/768/390/320 PASS with focus/Tab/prefill and no overflow/exceptions.
[Design, exact files, evidence, limitations and owner instructions](../../project-knowledge/chatbot/UNIFIED_FAQ_2026-11-11.md).
The browser preview is read-only synthetic; integrated Production acceptance is not claimed.

Local commit only. No push, merge, deployment, Production data/provider/secret change.
Original dirty checkout, branches, worktrees and unpublished history preserved.
