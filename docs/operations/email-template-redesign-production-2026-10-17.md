# EMAIL-TEMPLATE-REDESIGN-001 Production release — 2026-10-17

## Released source

- Exact application commit: `e4624c0ca9732f08654c10a30db8ec99fc4bff01`.
- `origin/main` advanced from `6f8cc0b` to the exact application commit. The unrelated local
  account-deletion documentation commit was explicitly excluded from this release.
- GitHub Actions run `38947149530` completed with Backend and Frontend `success`.

## Provider deployment evidence

| Surface | Evidence |
| --- | --- |
| Vercel Production | Deployment `dpl_7rbMhAeqPRPy5YbQsqhxKuxdtgHU` is Ready for the exact SHA and has the canonical public domain assigned. |
| Render Production API | Deployment `dep-db96nsrm8hqs73e4s43g` is Live for the exact SHA after a 57.7-second automatic deploy. |
| Supabase Production Edge | `email-worker` reported a successful update; its source matched the exact pushed `core.ts`, update time advanced and deployment count changed from one to two. |

## Read-only verification

- Public API liveness: `alive`.
- Public API readiness: `ready`; database and Redis `ok`; email and Storage `configured`.
- Canonical public frontend: HTTP 200.
- The existing Supabase function secrets, Cron schedule, JWT setting and provider configuration
  were not changed.
- No migration, account/database/DNS/secret mutation or real transactional email was used for this
  release check.

## Remaining evidence boundary

Automated local and CI coverage proves branded HTML generation, exact CTA paths, escaping,
plain-text fallbacks and provider propagation. Gmail/Outlook client rendering and a real
transactional-email delivery remain untested and are not claimed.

Result: **DONE — PUSHED / CI PASS / PRODUCTION VERIFIED**.
