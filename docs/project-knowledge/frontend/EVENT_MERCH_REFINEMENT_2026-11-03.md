# Event navigation and Merchandise refinement — 2026-11-03

Local review only, branch `codex/event-merch-refinement`, baseline verified remote main `5a7bb90`.
No push, merge, deployment, provider/database/auth/Storage change. Render setting was not accessed
or changed; retain the previously recorded Auto-Deploy OFF state.

## Root causes and changes

Slider links contained only the Event UUID. Detail recognized only `from=user-dashboard`, so every
other URL returned `/`. Slider now appends `?from=landing`; detail recognizes exactly one allowlisted
origin and returns `/#events` with localized Back to Events wording. Query state survives refresh,
new tabs and copied URLs. Dashboard stays `/user/events`; absent/unknown/duplicate origins keep `/`.
Landing's existing hash scrolling is reused with a 7rem Events scroll margin above the sticky header.
API payload/schema, registration and visibility rules are unchanged.

Merchandise retains `/merchandise` and its `/#events` action. Cream community tokens, green and
orange accents, Poppins, responsive columns, Coming Soon badge and decorative shirt/tote concepts
replace the placeholder. EN/DE copy explicitly says nothing is available to buy. No purchase action,
pricing, dates, or availability promises. Artwork is hidden from assistive technology; no animation.
The Recap branch's prior rendering remains unchanged.

The previous junction command returned Access denied; no ACL/security diagnosis was established.
This worktree had no usable local dependencies. Package root is `apps/web`, standalone npm with
`package-lock.json`; Node24.11.0/npm11.6.2. Normal `npm ci` encountered sandbox registry ENOTFOUND;
retrying the same install with network access installed436 packages. No version/lockfile changes,
Administrator session, junction or permission/security setting changes were needed. Sandbox temp
module reads prevented4 test suites loading; the same focused tests ran outside that boundary.
Browser localhost access likewise required execution outside sandbox network isolation.

## Verification

TypeScript, repository frontend ESLint, focused Prettier and production build PASS (existing
large JS chunk advisory). Five focused files:37 tests PASS after updating the live-slider assertion
for the intended query parameter. No backend suites run.
Browser:18 recorded cases, EN/DE ×1440/768/390 for Merchandise and loaded fixture detail,
plus6 slider/refresh/browser Back cases.12 axe runs:0 WCAG A/AA violations;0 overflow;0 uncaught
JS errors. Back anchor clears sticky header, reduced-motion transitions none. Direct fallback and
Dashboard-origin link target verified; Dashboard interaction covered by existing focused test.
Desktop English/mobile German screenshot layouts visually inspected. Real authenticated Dashboard
and Production checks are outside this local task. Event fixture is synthetic and anonymous.

## Local review and restart

- Landing slider: http://127.0.0.1:5196/#events
- Detail: http://127.0.0.1:5196/events/11111111-1111-4111-8111-111111111111?from=landing
- Merchandise: http://127.0.0.1:5196/merchandise

The preview uses the real frontend with an explicitly invoked read-only localhost fixture middleware.
No permanent mock authentication; auth remains anonymous and all writes return405. Preview-only
public Event flag is enabled in process; production build flags/configuration are untouched.
The synthetic cover URL deliberately fails and exercises the existing local campus fallback.

Windows PowerShell (stop an existing copy with Ctrl+C before restarting):

```powershell
Set-Location 'C:\Users\phuoc\Downloads\buddyWebVer2\.local\worktrees\event-merch-refinement\apps\web'
# Only if dependencies are missing:
npm ci
node scripts/review-event-merch.mjs
```

Use the Navbar language selector (mobile menu on narrow screens). Review server uses strict port5196.
Local evidence: `.local/review/browser-results.json`,12 screenshots `merchandise-{en,de}-{1440,768,390}.png`
and `event-{en,de}-{1440,768,390}.png`, plus `verify.cjs` and server logs. These generated files are not
committed. No before screenshots were captured in this task.

## Modified files

Slider component and its test; live-section test; Event detail and its test; Coming Soon page;
community/landing CSS; EN/DE common locales; explicit local preview script; task/handoff/plan/index,
validation and Project Knowledge records. Existing uncommitted draft was continued in place.

Keyboard Tab reaches the Merchandise return link with visible focus; Enter returns to #events: PASS.
