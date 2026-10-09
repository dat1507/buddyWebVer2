# FE-LANDING-BG-002 — Landing slideshow performance and smooth transitions

**Feature group:** Landing page
**Priority:** Phase 2 corrective follow-up
**Status:** IMPLEMENTED — LOCAL VERIFIED / RELEASE PENDING
**Dependencies:** `FE-LANDING-BG-001` Production slideshow.

- **Objective:** remove the visible hitch/flicker at slideshow boundaries while retaining the exact
  five images, order, Hero design and seven-second/one-second timing feel.
- **Scope:** image decode gating, stable two-layer double buffering, opacity-only compositing,
  timer/visibility lifecycle, focused tests and direct desktop/mobile multi-loop verification.
- **Out of scope:** image replacement/reordering, Landing layout/content, Navbar, Event slider,
  Profile/Home University, authentication, matching, backend, database and unrelated Production
  configuration.
- **Relevant modules:** `hero-background-slideshow.tsx` and its focused test only; documentation
  control-plane records.
- **Acceptance:** next image is decoded before fade; only the fully transparent layer changes
  source; exactly one timer phase is active; hidden tabs pause the display interval; reduced motion
  stays static; three complete loops including 5 -> 1 pass without blank/flicker, overflow, layout
  shift, console errors or new resource duplication.
- **Release:** direct-to-`main` commit/push and Git-connected Vercel Production verification are
  explicitly authorized by the owner for this task.

## Baseline diagnosis — 2026-10-09

- Production used two `<img>` elements but did not invoke `HTMLImageElement.decode()` or wait for
  the incoming image to be decoded.
- Completion updated `currentIndex`, `nextIndex` and `transitioning` together. React therefore
  changed both element sources at the boundary (`[0,1]` -> `[1,2]`): the incoming visible texture
  moved to another DOM element while the just-visible incoming layer was immediately repurposed.
- The component scheduled two independent timeouts per cycle and did not pause visible-time
  accounting while the document was hidden.
- Production resource timing showed cached current/next assets loaded, so network transfer alone
  does not explain the owner-observed hitch. The unsafe source/texture swap and absent decode gate
  remain deterministic risks, amplified by cold cache, slow decode and low-end GPU/main-thread load.

## Implementation — 2026-10-09

- Retained exactly two physical image layers. A completed crossfade now flips the active layer and
  changes only the fully transparent outgoing layer to the following source; the visible image no
  longer moves between DOM elements at a boundary.
- Gated every fade on `HTMLImageElement.decode()` (with a load-complete fallback) so the incoming
  bitmap is ready before opacity changes begin. A decode/load failure leaves the current decoded
  image visible.
- Made CSS `transitionend` the completion signal. This avoids repurposing a source before a delayed
  compositor frame has actually reached zero opacity; the fixed transition-completion timeout was
  removed.
- Reduced scheduling to one visibility-aware display timer and no timer during the CSS transition.
  Hidden-document time is excluded, timer/listener cleanup is deterministic and reduced-motion
  users receive one static first image with no slideshow timer.
- Added paint containment and a bounded `will-change: opacity` hint to the existing two layers. The
  five WebP assets, their order and their total 890,342-byte payload are unchanged.

## Local verification — 2026-10-09

| Check | Result |
| --- | --- |
| Complete frontend tests | 77 files; 730 tests PASS |
| Focused slideshow + assembled Landing tests | 2 files; 13 tests PASS |
| Slideshow lifecycle coverage | decode gate, hidden display/transition, 3 loops/15 transitions, 5 -> 1, timer cleanup and reduced motion PASS |
| TypeScript / ESLint / Prettier | PASS / PASS / PASS |
| Production build | PASS; existing large-chunk warning only |
| Real-browser loop audit | 16 transitions across desktop/mobile; correct order including 5 -> 1 |
| Blank or undecoded-visible samples | 0 / 2,522 samples |
| Source changes while source layer visible | 0 / 16 |
| Minimum combined layer opacity | 1.0000 |
| Slideshow layout delta / horizontal overflow | 0 px / 0 px |
| Layer bound | exactly 2 throughout normal-motion audit |
| Reduced motion | one static first image; no animated layer pair |
| Reload | first two images complete; first image visible; no overflow |
| Browser console | 0 errors; 0 warnings |

The first post-implementation browser trace also exposed why a duration-matched completion timeout
was unsafe: in an occluded/throttled rendering interval, `transitionrun` began about 987 ms after
the React phase update. Waiting for the outgoing layer's actual `transitionend` removed that race;
the repeated audit then reported zero visible-layer source changes.
