# EMAIL-TEMPLATE-REDESIGN-001 — Align verification and accepted-invitation emails

**Status:** DONE — PUSHED / CI PASS / PRODUCTION VERIFIED
**Priority:** P1
**Track:** auth-email / buddy-v2
**Assigned:** 2026-10-16
**Dependencies:** `EMAIL-002`, `INV-008`, `INV-009`, `MAIL-001`

## Objective

Redesign Email Verified and Accepted Invitation so their HTML presentation reuses the current
Received Invitation visual system while preserving all verification, invitation, Match,
conversation, recipient-resolution, retry and security behavior.

## Scope and sequence

1. Inspect the three renderers, both delivery runtimes, branding asset, event payloads, URLs and
   focused tests.
2. Extract the Received Invitation header/card/content/button/footer design into a small shared
   renderer in each existing runtime.
3. Add branded HTML to Email Verified without changing sealed-token generation, expiry or URL.
4. Add branded HTML to Accepted Invitation without changing the authoritative recipient/
   conversation resolver or deep link.
5. Keep both delivery runtimes consistent, update tests, render local previews and run relevant
   regression/static gates.

## Guardrails

- Supabase Edge remains the Production worker; Python remains the local/debug fallback.
- Keep existing event names, payload allowlists, idempotency keys, current-address rules, same-origin
  URL construction and plain-text fallbacks.
- Do not change verification issuance/confirmation, invitation acceptance, Match or conversation
  creation, provider configuration, schema or Production state.
- The current templates are deterministic English only; do not introduce a new localization system
  in this presentation-only task.
- Do not commit, push or deploy without separate owner authorization.

## Task 0 inspection — complete 2026-10-16

- Production delivery is `transactional_outbox -> Supabase Cron -> email-worker Edge Function ->
  Resend`; the Python outbox worker uses the same provider-neutral contracts as a local/debug
  fallback. Both paths must render equivalent templates.
- Received Invitation is `MATCHING_INVITATION_CREATED`, implemented in
  `app/services/invitation_email.py` and `supabase/functions/email-worker/core.ts`. It is the only
  one of the three with branded HTML: a 600 px table shell, gray page, white rounded card, black
  header/footer, same-origin `/vguBuddy_logo.png`, orange label/button and mobile media query.
- Email Verified is `EMAIL_VERIFICATION_REQUESTED`, implemented in
  `email_verification_requests.py` and the Edge worker. Its payload contains only sealed token
  material and expiry. Rendering decrypts only in memory and builds the existing same-origin
  `/verify-email?token=...` URL; it currently returns plain text only and states the 15-minute
  expiry/security instruction.
- Accepted Invitation is `MATCHING_INVITATION_ACCEPTED`, implemented in
  `invitation_email.py` and the Edge worker. Its resolver revalidates the accepted invitation,
  original sender's current verified address, ACTIVE Match and exact conversation, then renders
  `/user/buddy?conversation=<UUID>`; it currently returns plain text only.
- The existing logo is `apps/web/public/vguBuddy_logo.png`, exposed from the configured public app
  origin. Provider contracts already support HTML plus plain-text fallback. No template engine,
  external stylesheet, language payload or alternate localized variant exists.
- Focused Python coverage is in `test_email_verification_request_service.py`,
  `test_invitation_email.py` and `test_invitation_email_edge_contract.py`; Edge behavior is covered
  by `supabase/functions/email-worker/core.test.ts`. Existing auth/invitation event tests protect
  token, recipient, outbox and acceptance behavior.

No migration, new event, route, dependency or localization subsystem is required.

## Tasks 1–4 implementation — complete 2026-10-16

- Added a small shared, table-based branding renderer to each existing delivery runtime. Both use
  the Received Invitation shell: light-gray page, 600 px white rounded card, black branded
  header/footer, same-origin VGU Buddy logo, orange accent/button and the existing mobile media
  query. Dynamic text and URL attributes are escaped at their appropriate boundaries.
- Refactored Received Invitation to use the shared renderer without changing its subject,
  plain-text body, CTA, sender data or destination.
- Added branded HTML to Email Verified with the existing verification link, visible fallback link,
  15-minute expiry and security notice. Sealed-token issuance, in-memory decryption, event payload
  and confirmation behavior are unchanged.
- Added branded HTML to Accepted Invitation with the escaped acceptor name and the existing
  authorized conversation deep link. Current-address recipient resolution, accepted-invitation
  revalidation, ACTIVE Match lookup and exact conversation lookup are unchanged.
- Kept the Python fallback and Production Edge worker equivalent and retained every plain-text
  fallback. No dependency or language mechanism was introduced: the repository has no localized
  transactional-email variants to update, and these templates remain deterministic English.

## Task 5 validation — complete 2026-10-16

| Check | Result |
| --- | --- |
| Focused Python email rendering/contract tests | 13 PASS / 16 deselected |
| Relevant auth/invitation regression set | 96 PASS |
| Supabase Edge worker tests | 15 PASS |
| Full backend | 1,417 PASS / 37 explicit live-environment SKIP; disposable Python 3.12 container |
| Ruff / strict mypy | PASS / PASS (293 source files) |
| Edge TypeScript tests / Prettier | PASS / PASS |
| Frontend TypeScript / ESLint / Prettier | PASS / PASS / PASS |
| Backend package / frontend Production builds | PASS / PASS; existing frontend large-chunk advisory only |
| Python dependency integrity | PASS |
| Side-by-side local preview artifact | Generated for Received, Verification and Accepted templates with deterministic sample data |
| Gmail / Outlook / interactive browser visual acceptance | NOT RUN; no claim of client-specific rendering |
| Release | `e4624c0`; GitHub Actions `38947149530` PASS; Vercel, Render API and Supabase `email-worker` deployed |
| Schema / Production boundary | No migration or Production account/database/provider-configuration write |

The local preview gallery exercises all three Python-rendered templates and embeds the repository
logo only for offline viewing. Automated coverage checks equivalent shared structure, mobile CSS,
exact CTA routes, click targets, fallback text, expiry/security text, dynamic-name escaping and
provider HTML propagation in both runtimes. A browser preview attempt could not access the local
preview from the sandboxed in-app browser, so responsive Gmail/Outlook rendering remains an
explicit evidence gap rather than a claimed pass.

## Acceptance

- All three messages share the Received Invitation header, card, typography, button and footer
  primitives in both runtimes.
- Verification retains the exact issued token URL, 15-minute expiry and security text, including a
  usable fallback link.
- Accepted Invitation identifies the escaped acceptor and retains the exact authorized conversation
  deep link.
- Plain-text fallbacks, HTML escaping, mobile constraints, provider HTML propagation and dynamic
  field tests pass without changing business logic.

## Result

**DONE — PUSHED / CI PASS / PRODUCTION VERIFIED.** Commit
`e4624c0ca9732f08654c10a30db8ec99fc4bff01` reached `origin/main`. GitHub Actions run
`38947149530` passed Backend and Frontend. Vercel Production deployment
`dpl_7rbMhAeqPRPy5YbQsqhxKuxdtgHU` is Ready for the exact commit and serves the canonical public
domain. Render deployment `dep-db96nsrm8hqs73e4s43g` is Live for the same commit. The Supabase
Production `email-worker` accepted the exact pushed `core.ts`, reported a successful update and
advanced from one to two deployments. Public API live/readiness and the public site pass after
release. No schema, account, database or provider-configuration mutation occurred. Gmail/Outlook
rendering and a real transactional-email send remain unclaimed.
