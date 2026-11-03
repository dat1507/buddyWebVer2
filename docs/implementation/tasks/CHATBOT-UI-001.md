# CHATBOT-UI-001 — Phase 3.4 floating chatbot frontend

**Assigned:** 2026-10-24 (Asia/Saigon), explicit owner pasted request.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.
**Baseline:** clean `main` at `a133a597618cecd51cfb262c32a052a2cdbb3edc`.

Implement a default-OFF floating public/user chatbot, excluding Admin workflows, at a shared
route boundary. Reuse current React/Vite design tokens, EN/DE locale, API base and request/error
patterns, icons and test tools. Lazy panel, mobile dialog/desktop non-modal behavior, safe text
and typed public citations, bounded in-memory independent-question turns, cancellation/order/
retry/rate-limit handling and accessible keyboard/focus/live announcements. No persistent history.

Focused source: app/router/layout integration, feature flag, chatbot components/styles/client,
locale additions and targeted component/API/layout tests. Inspect Phase 3.3 DTOs; preserve backend,
all eight corpus files, 17 FAQs/nine exclusions, disabled providers, auth and existing routes.
No dependency/cloud/billing/database/Production changes, push or deployment. Local `main` commit.

Validation: focused UI/API/keyboard/cancellation/rate/schema tests, existing layout/public/User/
Landing/Navbar/slider/resource/EN-DE regression, TypeScript/ESLint/format/build and bundle impact.
Real loopback frontend-to-backend EN/DE/citations/miss/sequential/unavailable/429, desktop/tablet/
mobile/narrow visual/focus/overflow/reduced-motion checks; report virtual-keyboard/environment
limits accurately. Update focused knowledge, task/control-plane/handoff/index and validate paths.

## Acceptance — 2026-10-24

One default-OFF public/USER widget mounted above layouts, Admin excluded; lazy widget/panel,
EN/DE labels, actual DTO/source validation, plain-text answers and independent in-memory turns.
Exact public POST exception in the existing transport omits cookies/CSRF; all other routes retain
their prior behavior. Bounds, cancellation/order/retry/cooldown, error containment and accessible
desktop/mobile focus/scroll behavior implemented without dependencies or backend changes.

**904 tests / 90 files PASS** full frontend regression; **89 / 4 files PASS** final focused set
after the keyboard-scroll/focus-loop adjustment. TypeScript/affected ESLint/format and flag-ON/OFF
production builds PASS. Existing large-entry warning retained. Real browser/API EN/DE/source/miss/
sequential/503/backend-down/429 and responsive/keyboard checks PASS. Production preview with flag
OFF has no launcher. Disposable API guards: no external/provider/private DB attempts.

No physical mobile keyboard, hardware screen reader, light-mode or reduced-motion browser
emulation claimed; fixed-dark site and available developer-control limitations are documented.
The widget fits 320px; an existing 329px German Landing width is reproduced with flag OFF and
left for separate scope. Synthetic USER exposure tests, not real account/login acceptance.
All eight corpus files/17 verified FAQs/nine exclusions, API/providers/auth source and legacy
history preserved. No Production/cloud/account/database/billing, push/deploy or paid dependency.

See [focused guide](../../project-knowledge/chatbot/PHASE_3_4.md) for exact commands, evidence,
initial corrections, bundle measurements and release limits. Local commit after integrity checks;
no next implementation task assigned. Phase 3.5 release evaluation requires separate selection.
