# FE-LANDING-CTA-001 — Simplify the Landing call to action

**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED
**Priority:** P1
**Track:** frontend
**Assigned:** 2026-10-16
**Dependencies:** `FE-LANDING-BG-001`

## Objective

Modify only the Landing section titled `Ready to Transform Your University Experience?`: remove
the Watch Demo action and its exclusively associated video surface, then horizontally center the
existing Join the Community action at desktop, tablet and mobile widths.

## Scope

- Preserve the section background, ambient glow, typography, copy, registration destination and
  all other Landing sections.
- Remove only demo-specific state, handlers, imports, localization, component/tests and media that
  have no other repository consumers.
- Keep shared UI, modal-isolation and media infrastructure that remains used elsewhere.
- Add focused regression coverage for one centered registration action and absence of demo UI.
- Run focused tests plus frontend formatting, lint, type-check and production build.
- Do not push or deploy without a separate explicit request.

## Implementation

- The CTA now renders only the existing `/register` action inside a centered flex container.
- The action remains full width on mobile and returns to its intrinsic width at the existing `sm`
  breakpoint.
- Demo-only state, imports, dialog implementation, tests, localization strings, poster and video
  were removed after repository search confirmed that they had no other consumers.
- Shared modal isolation and all other Landing sections remain unchanged.

## Verification — 2026-10-16

| Check | Result |
| --- | --- |
| Focused CTA/Landing tests | 2 files / 13 PASS |
| Full frontend regression | 85 files / 810 PASS |
| TypeScript / ESLint / Prettier | PASS / PASS / PASS |
| Production build | PASS; existing large-chunk advisory only |
| Rendered responsive check | 1440×900, 768×1024 and 390×844: center delta `0 px` |
| Removed demo surface | One CTA action; no Watch Demo text, dialog or video at all three viewports |
| Browser console | 0 errors with the auth bootstrap isolated by a local response fixture |
| Deployment | Not pushed or deployed; no deployment authorization was granted |

The resulting local commit is reported in the completion handoff because a commit cannot include
its own identifier. Production remains on the previously verified Event synchronization release;
this CTA change is not claimed live.
