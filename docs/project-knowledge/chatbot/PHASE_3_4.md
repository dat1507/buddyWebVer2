# Phase 3.4 — floating public FAQ interface

2026-10-24 (Asia/Saigon), [CHATBOT-UI-001](../../implementation/tasks/CHATBOT-UI-001.md).
Source baseline: clean `main`, `a133a597618cecd51cfb262c32a052a2cdbb3edc`.
Implemented and verified locally; no push, deployment, Production configuration or account change.
This continuation supersedes earlier no-frontend statements for local source only.

## Components and request boundary

[App](../../../apps/web/src/App.tsx) mounts one
[ChatbotEntry](../../../apps/web/src/features/chatbot/chatbot-entry.tsx) outside individual layouts.
Exact `VITE_CHATBOT_ENABLED=true` enables it on public Landing/auth/information/Event paths and
authenticated USER paths. Admin sessions, `/admin`, `/adminLogin` and unknown routes are excluded.
Visibility uses the existing auth presentation store; it adds no authorization or database lookup.
Supported navigation keeps the mounted session; identity changes and unsupported routes clear it.
Existing routes, including the separate assistant placeholder, retain their previous behavior.

| Module                                                                             | Responsibility                                                                                    |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| [Widget](../../../apps/web/src/features/chatbot/chatbot-widget.tsx)                | Lazy feature, shared launcher/open state, cancel-on-close and focus restoration                   |
| [Panel](../../../apps/web/src/features/chatbot/chatbot-panel.tsx)                  | Loaded on interaction; welcome, messages, sources, composer, responsive accessibility             |
| [Conversation](../../../apps/web/src/features/chatbot/use-chatbot-conversation.ts) | At most 20 turns, one active request, draft, retry cooldown, cancellation/stale-response fence    |
| [Client](../../../apps/web/src/features/chatbot/chatbot-client.ts)                 | Real DTO validation, Unicode bounds and vetted public URLs using existing Zod                     |
| [Boundary](../../../apps/web/src/features/chatbot/chatbot-boundary.tsx)            | Contains optional chunk/render failures; localized, dismissible failure without breaking the page |
| [Styles](../../../apps/web/src/features/chatbot/chatbot.css)                       | Scoped existing color tokens, safe areas, scroll regions and viewport sizing                      |

Flow: launcher → lazy panel → `{ question }` → existing `requestJson`/Vite proxy →
`POST /api/chatbot/query` → unchanged verified retrieval → validated response → plain text/sources.
No knowledge data, retrieval algorithm, model SDK, private-user tool or provider selector enters
the frontend. The [Phase 3.3 contract](PHASE_3_3.md) remains authoritative and unchanged.

The existing [transport](../../../apps/web/src/lib/api.ts) had required CSRF for every non-GET.
Only exact POST `/chatbot/query` is now a public stateless-read exception: cookies omitted, no CSRF
header/acquisition, no-store and an eight-second client deadline. All neighboring paths/methods
retain credentialed CSRF behavior and the existing 15-second timeout. No auth bootstrap/refresh is
initiated by the chatbot. Signed-in users receive the same public data as anonymous visitors.

## State, content and privacy

Each request sends just its own question. Previous turns are visual history, not multi-turn model
memory. Messages and drafts stay in component memory only: close/reopen preserves completed turns;
reload, clear, identity change or leaving supported routes removes them. No browser storage, server
history, polling or analytics is added. The existing locale storage is unchanged.

Input accepts normal EN/DE, punctuation, tabs/newlines and at most 500 Unicode code points. The
textarea's 1000 UTF-16-unit editing ceiling allows 500 supplementary characters; invalid/long drafts
cannot be sent. Enter submits, Shift+Enter inserts a line, IME composition does not submit. Send
stays disabled while pending, but the next draft remains editable. An immediate ref fence prevents
duplicate requests before React commits. Late replies from aborted/cleared/retried requests are ignored.

HTTP 200 answers, uncertainty, restrictions and language choice are successful messages. Website
locale controls UI/welcome; backend `language` controls answer `lang` and text. No factual answer
is created or rewritten in the UI. Sources retain IDs/dates and actual public reference titles.
Repository evidence is a plain guide citation with no invented link. URLs must match the backend's
HTTPS university-domain family, without userinfo/query/fragment/control characters or custom ports.
Unknown response fields, inconsistent support/status, bad dates or unsafe URLs fail safely.
React renders all answer/question/reference text; there is no HTML or Markdown interpretation.
External links use `noopener noreferrer`, no-referrer and a localized new-tab announcement.

Errors are localized categories, never raw response bodies or diagnostics: validation, network,
timeout, rate limit, unavailable/disabled, server and invalid response. Retry reuses the same failed
turn; it does not append another question. There is no automatic retry. `Retry-After` disables send
and retry during a local countdown (no per-second live announcement), including across clear/close.
Missing/malformed 429 retry information uses a conservative 60-second UI wait. Real backend values
are bounded; defensive UI handling clamps extreme numeric waits to one day. Clear does not reset
an active cooldown. The backend remains the abuse-control authority.

## Responsive and accessible behavior

Desktop/tablet: approximately 400px floating panel, constrained to viewport height, non-modal named
region; other navigation stays accessible. Mobile below 640px: full-height dialog above the sticky
navbar, modal semantics, existing `useModalIsolation`, page scroll lock, safe areas and a keyboard
focus loop. VisualViewport resize/scroll listeners keep header/composer within a reduced visible
viewport and are removed on unmount. A resize back to desktop restores normal page behavior.

Opening focuses the textarea; closing/Escape restores launcher focus when it remains mounted.
The scrollable `role=log` is focusable for Home/End/PageUp/PageDown navigation with visible focus;
message scrolling does not scroll the page. Pending/error/live-message semantics are localized.
Existing Button focus styles and motion-reduce behavior are reused; spinner animation is only
motion-safe. No animation library, state manager or new dependency is added. Optional widget errors
are contained locally rather than crashing the surrounding app.

## Verification and limits

- **Full frontend: 90 files / 904 tests PASS** (443.77 s), including Landing, Navbar, slider,
  resources, public/User/Admin layouts, auth/session, routes, locale and shared transport regression.
- **Focused final: 4 files / 89 tests PASS**, after the final keyboard-scroll/focus-loop adjustment.
  Covers UI, actual DTOs, URL/XSS boundaries, cookies/CSRF isolation, validation, language, ordering,
  cancellation/stale responses, retry/cooldown, mobile semantics and route/identity/flag exposure.
- TypeScript, affected ESLint and formatting **PASS**. Production builds with frontend flag ON
  and OFF **PASS**; existing large-entry warning retained. No backend regression was repeated:
  backend source/corpus is unchanged; real browser integration exercises the existing endpoint.
- Build-reported deferred assets: widget 4.25 kB / ~2.01 kB gzip; panel 6.55 kB / ~2.39 kB gzip;
  scoped CSS 4.55 kB / ~1.31 kB gzip. ON/OFF entry difference 707 minified bytes. These compare
  flag modes, not an independently rebuilt pre-feature baseline. OFF still emits optional chunks,
  but does not mount/fetch the widget or call its API. No KB or new dependency is bundled for it.

Actual Brave → Vite proxy → Uvicorn → packaged retrieval → UI checks passed: anonymous English,
German, EN answer under DE UI, official/code sources, unsupported fallback, multiple sequential
and long German questions, safe backend-stopped failure, real disabled/503 and local quota/429.
The real 429 wait disabled retry, made no automatic request and manually recovered with one question
bubble. Disposable server guards recorded **zero external connections, provider calls and private
database attempts**. Its ephemeral auth/CSRF signing fixtures enabled anonymous bootstrap without
real credentials or accounts. Authenticated USER exposure/identity reset is tested with the existing
store's synthetic fixtures; no live login/account acceptance is claimed.

Responsive browser checks: 1440×900, 768×1025, 390×844 and 320×800; long messages, source wrapping,
open/closed states, header/close/input bounds, Escape/focus restoration and mobile isolation pass.
A 390×400 short viewport retained the composer/header and a 209px message scroll area. Keyboard
Home scrolled a 1384px chat history to top without moving the page. Widget itself has no horizontal
overflow. **Existing DE Landing width is 329px at a 320px viewport**, reproduced in the flag-OFF
production preview with no widget; left unchanged as a separate layout issue. 390px+ checks show
no page overflow. The initial mobile navbar stacking problem was fixed in scoped widget CSS.

The site currently fixes `class=dark`; no light-mode UI control exists. Dark mode is visually
verified; light-mode and reduced-motion browser emulation are not claimed (raw CDP was unavailable).
Reduced-motion classes are code-reviewed. No physical mobile keyboard/device, hardware screen reader
or deployed browser acceptance is claimed; VisualViewport/short-screen and automated ARIA/focus
checks are the available evidence. These are release-evaluation limits, not external inference gates.
Screenshots are local ignored artifacts under `.local/phase34-visuals/`.
All temporary API/dev/preview servers were stopped and browser viewport overrides restored.

Initial issues: wrong working directory for one npm invocation; Windows sandbox transform-temp
ENOENT; corrected cooldown timer, synthetic user timestamp, throwing-fixture type and focus-order
test failures. Final checks pass with workspace TEMP/TMP. A redundant narrowed regression was
cancelled after the full 904-test result arrived; it is not counted as a pass.

## Run locally

Use the installed environments; do not change Production variables. Backend PowerShell:

```powershell
cd C:\Users\phuoc\Downloads\buddyWebVer2\apps\api
$env:APP_ENV='local'
$env:RATE_LIMIT_STORAGE_URI='memory://'
$env:CHATBOT_API_ENABLED='true'
$env:CHATBOT_AI_ENABLED='false'
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --no-proxy-headers --no-access-log
```

Frontend in another PowerShell window:

```powershell
cd C:\Users\phuoc\Downloads\buddyWebVer2\apps\web
$env:VITE_CHATBOT_ENABLED='true'
$env:VITE_API_URL='/api'
$env:LOCAL_API_PROXY_TARGET='http://127.0.0.1:8010'
npm.cmd run dev -- --host 127.0.0.1 --port 5180 --strictPort
```

Open `http://127.0.0.1:5180/`. Try `How do I register?`, `Wie registriere ich mich?`, `What is VGU?`
and `What is the weather on Mars?`. Public chatbot needs no auth/database/provider credentials;
normal session bootstrap and private features still need their separately documented local settings.
Without those, an existing session-unavailable notice can coexist with a working public chatbot.
For ordinary credentialed application development use the existing approved auth/CORS environment;
the fixture guard server used for this acceptance is not an account-testing environment.

Set frontend flag false/unset and restart Vite/rebuild to hide it. Backend flag remains separately
default OFF; setting it false and restarting produces the friendly 503 state. No browser parameter
can activate backend AI. Both provider implementations/eligibility gates remain unchanged.

```powershell
# From apps/web; stable Windows workspace temp for Vitest workers.
$env:TEMP=(New-Item -ItemType Directory -Force .local/phase34-test-tmp).FullName
$env:TMP=$env:TEMP
npx.cmd vitest run --maxWorkers=1 --no-file-parallelism
npx.cmd vitest run src/features/chatbot src/lib/api.test.ts --maxWorkers=1 --no-file-parallelism --no-cache --reporter=dot
npm.cmd run typecheck
npx.cmd eslint src/features/chatbot src/lib/api.ts src/App.tsx
npx.cmd prettier --check src/features/chatbot src/App.tsx src/lib/api.ts src/locales/en/common.json src/locales/de/common.json
npm.cmd run build
```

## Next boundary

Phase 3.5: separately assign release-readiness evaluation, including real-device keyboard/screen
reader checks, the narrow German Landing issue, and acceptance of the existing process-local
limiter/proxy/access-log limits before any public rollout. Keep both deployment flags OFF.
Phase 3.6, if selected: resolve provider eligibility/privacy/license and hard zero-cost gates before
any external inference work. No provider/service/billing activation, dependency change or additional
operating cost occurred in Phase 3.4.
