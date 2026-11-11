# Unified FAQ management — 11 November 2026

Implementation: `6dec701e03ebf412b122fb9017523815de655839` on `codex/admin-kb-unified`, based on freshly fetched
`deef12c0a04cafc2a36c5e7639d2a83301c0bb2c`. Local owner acceptance pending.
The original dirty checkout, other branches/worktrees, main and Production were preserved.

## Design and workflow

One FAQ list combines all 28 packaged entries and managed identities, using the generic FAQ label.
A `builtin_id` replacement occupies its original row; its saved draft remains available in Edit.
View shows the published revision when present; an unpublished replacement shows its built-in
fallback. Stand-alone unpublished FAQs show their saved draft. Both languages, aliases, answers,
category, source references, available verification dates and revision pointers are shown.
Original verification is displayed only for original content, never attributed to a replacement.

Existing APIs expose neither complete packaged content nor the effective published revision.
The additive ADMIN-only `GET /api/admin/knowledge-base/catalog` composes those in one SQL snapshot
with packaged entries; existing endpoint shapes and mutation code are unchanged. No migration,
knowledge copying into PostgreSQL, dependency, new AI, feature flag or retrieval change.

Search uses casefolded literal substring matching over EN/DE questions, aliases and answers in the
published/original content and saved draft, including original text after a replacement is published.
Category filters follow the displayed content; publication filters follow the managed workflow status
when a managed identity exists. A draft/unpublished replacement can therefore still have an active
original fallback, explicitly explained in View. Otherwise verified originals are Published and the
11 excluded/unverified/conflicting/outdated packaged references are Unpublished. Filter first,
then stable 20-row pagination; a linked replacement is deduplicated before both operations.
Clearing the search clears the active search; Clear search and filters resets everything to page 1.

Edit reuses the existing editor, optimistic versions, draft save, preview, explicit publish/unpublish,
append-only history, restore confirmations, audit, ADMIN/RBAC and CSRF. New FAQ behavior is unchanged.
Built-in editors prefill both languages and aliases but keep evidence unsupported and source fields
empty. Code/official provenance is never converted into Admin evidence. Existing restrictions on
links, private details, high-risk topics and stable public VGU sources still apply; prefilled content
may require revision before saving. Nonverified references cannot be replaced by the verified-FAQ
workflow; the existing rejection now gives an actionable explanation. Public precedence, cache
refresh timing and built-in fallback remain as documented in [the original task](../../implementation/tasks/ADMIN-CHATBOT-KB-001.md).

Reference Sources links to the public GitHub file pinned to the baseline's full SHA and explicitly
labels it a repository snapshot that may differ from the running API artifact. The browser/GitHub
can view/download the original text. No guide content is loaded into the Dashboard, and no editor,
upload, sync or guide endpoint was added. Canonical blob remains
`b4c1ea6d9c527a585156840f3834762879a7aecb`; its bytes/encoding/line endings were not changed.
The exact pinned URL was read successfully through GitHub (21,614 characters).

## Verification

- Backend: 17 new catalog tests plus 233 existing chatbot/public API tests, all 250 PASS.
  Two existing file-fixture tests initially hit Windows temporary-directory permissions; both passed
  when rerun with an isolated writable temporary folder. No product failure was bypassed.
- Real PostgreSQL 17.11 lifecycle: 1 PASS (23.77 seconds), expanded with catalog assertions.
  The existing test checks runtime/RLS permissions, CSRF, stale writes, draft isolation, bilingual
  retrieval, two-worker publication refresh, unpublish, restore/history, audit and outage fallback.
  New assertions verify pending published-vs-draft content and one linked row before/after unpublish.
  Only a fresh disposable loopback cluster on port 64749 was used; the test dropped its test database
  and the task-owned cluster was stopped. No Production data or credentials were used.
- Frontend: 11 Knowledge Base tests plus 34 existing route/role guard tests, all 45 PASS.
  Includes New FAQ, preview selection, explicit publish/unpublish/restore, stale edit preservation,
  bilingual details, prefill, linked draft reuse, provenance, filters/pagination reset, retry and guide URL.
- TypeScript, affected ESLint/Prettier, Ruff format/lint and focused mypy PASS. Production build PASS;
  existing large-chunk advisory remains. Reused local dependencies: Vite 8.2.2, Vitest 5.0.0,
  TypeScript 6.0.3, React 19.2.8. No dependency or lock changes; not a fresh lockfile installation.
- Real headless Chrome: EN/DE at 1440/768/390/320, four screens each (32 cases), zero horizontal
  overflow or browser exceptions. View/Edit targets >=44px; detail heading focus, real Tab to Edit
  then Close, editor prefill and return focus verified. EN/DE 390px screenshots visually inspected;
  four separator encoding errors were corrected before final browser/build verification.
- Synthetic preview code and data are ignored under `apps/web/.local`; their marker strings are absent
  from the production build. No automated WCAG audit, physical-device or Production acceptance claim.

## Local owner review and limits

Open [the synthetic preview](http://127.0.0.1:5231/.local/kb-review.html) (EN), or add `?lang=de`.
1. Search `How do I register?`, `Buddy Matching`, or answer text; change category/status and clear filters.
2. Open View, inspect bilingual aliases/answers/sources, then Edit and inspect the prefilled draft.
3. Check the narrow layout and keyboard controls; open Reference Sources → View systemPrompt.txt.

The preview runs the real components with synthetic read-only data; saving/publishing are deliberately
unavailable there. It is not a browser-to-live-database acceptance claim. Full API mutation semantics
were exercised by the real local PostgreSQL test above. To repeat that test, start an explicitly
disposable PostgreSQL server with the existing fixture roles and run from `apps/api`:
`python -m pytest tests/test_managed_faq_live.py -q`, setting `RECAP_TEST_DATABASE_URL` to that server's
loopback `buddy_recap_local` URL. Never use Production. For normal local integrated use, run this
branch's API and frontend together and open `/admin/knowledge-base` with a local Admin session.

The read-only catalog filters the small Admin collection in memory after a single query; it is linear
in saved FAQ count and does not introduce search infrastructure. Frontend and additive API must be
released together later; existing clients remain compatible. Public activation remains subject to
existing validation, deterministic precedence and cache refresh, never automatic publication on save.
No push, merge, deployment, provider/environment/secret change or Production access.

## Exact implementation files

- `apps/api/app/api/admin_knowledge.py`
- `apps/api/app/services/faq_catalog.py`
- `apps/api/app/services/managed_faq.py`
- `apps/api/tests/test_faq_catalog.py`
- `apps/api/tests/test_managed_faq_live.py`
- `apps/web/src/features/admin-knowledge-detail.tsx`
- `apps/web/src/features/admin-knowledge-editor.tsx`
- `apps/web/src/features/admin-knowledge.ts`
- `apps/web/src/locales/de/common.json`
- `apps/web/src/locales/en/common.json`
- `apps/web/src/pages/admin/admin-knowledge-page.test.tsx`
- `apps/web/src/pages/admin/admin-knowledge-page.tsx`

Documentation files in the companion evidence commit:

- `SESSION_HANDOFF.md`
- `implementation-plan.md`
- `docs/implementation/task-index.md`
- `docs/implementation/validation.md`
- `docs/implementation/tasks/ADMIN-KB-UNIFIED-001.md`
- `docs/project-knowledge/chatbot/README.md`
- `docs/project-knowledge/chatbot/UNIFIED_FAQ_2026-11-11.md`

All 270 task files have unique matching index paths; focused documentation links and whitespace PASS.
