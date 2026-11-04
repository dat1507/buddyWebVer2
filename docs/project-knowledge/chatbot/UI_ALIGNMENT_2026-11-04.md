# Chatbot UI alignment — 2026-11-04

CHATBOT-DESIGN-001. DONE — LOCAL VERIFIED / NOT PUSHED OR DEPLOYED.
Baseline:6851725362184af7c85828602b6c881f64374b60, freshly verified origin/main and
Vercel Production dpl_2bmuqvAyM1RnJrCZhVdupmMXBza3. All newer Admin Event actions retained.
Dedicated branch codex/chatbot-ui-alignment; existing integration dirty release documents untouched.

## Design and implementation
Actual references: styles/landing.css (paper#faf6ee, ink#242a25, muted#596057,
orange#ae410b, line#d9d8ca; action#ff8a45/#ff9d62), EventsExploreMore24px rounded
sage/peach cards, BenefitsGrid20px white cards, community Merchandise rounded controls,
EventDetail rounded cards, shared Button/Poppins/Lucide. These current styles override older
dark utility defaults. Global dark mode remains intact; assistant intentionally uses the same
warm public surface as Landing/Merchandise on supported routes.

Move unchanged public palette values to index.css root so portal and Landing share tokens;
Landing primary action now reads identical shared values (no visual palette change).
Launcher retains56px target, restrained shadow, title/label, safe-area padding.
Panel432px max/672px max,24px corners, warm header, white answers, soft orange questions,
compact disclosure icons/metadata, wrapping links and full source/provenance preservation.
Header retains clear/close44px controls; input16px, visible contrast/focus ring and real pending
spinner. No gradients/fake streaming/delays/dependencies. Existing phase transitions remain220/180ms.

Empty state has localized heading and two optional FAQ buttons (account and matching), sourced
from existing verified website-register/website-matching topics. Clicking calls the unchanged
send flow and focuses textarea. Suggestions disappear during conversation; after Clear, they
respect existing cooldown. Existing scope/privacy text remains visible. No factual answer added.

Changed frontend: chatbot-widget.tsx, chatbot-panel.tsx, chatbot.css, chatbot-widget.test.tsx,
index.css, styles/landing.css, locales/en/common.json, locales/de/common.json.
API client, conversation hook, entry/flag, source schemas/classification, authentication,
entire backend/KB, Admin Events and dependencies unchanged (git diff checks). No migrations,
hosting/env/AI/cost changes; local review flags only.

## Verification
104 focused tests /5files PASS (88 chatbot including3 new suggestion/cooldown cases plus
16 affected Landing/ComingSoon route cases). TypeScript PASS; frontend ESLint PASS;
focused Prettier PASS; final Production build PASS with VITE_CHATBOT_ENABLED=true and local /api.
Existing bundle>500kB advisory remains, no new dependency. No backend regression suite.
Initial sandbox Vitest worker-temp ENOENT affected2 suites; authorized native rerun passed.

Browser: EN and DE at actual CSS1440x900,768x1025,390x844,320x720. Browser90% zoom was accounted
for when setting viewport; dimensions measured from DOM, not inferred from requested size.
All8 inspected screenshots have no document horizontal overflow, visible header/composer;
mobile full-height modal, background inert/body-scroll lock and independent message scrolling.
Final narrow header retains assistant icon. Desktop nonmodal/phone modal semantics retained.
EN registration suggestion and DE matching suggestion return real local retrieval answers,
citation disclosure shows original IDs/dates. German laundry retains qualification and original
untranslated quote. Local503/retry and429 feedback tested; existing unit cases cover network,
timeout, pending, fallback, cancellation, XSS-safe text, source links, keyboard and validation.
Manual mobile ShiftTab wraps first header control to textarea; Escape restores launcher and
cleans isolation/scroll lock; Enter opens with textarea focus. Reduced-motion emulation reports
animation:none.390x420 reduced-height check keeps header/composer visible (visualViewport).
Overrides reset and locale restoredEN.

Visual testing uses loopback-only8064 fixture calling unchanged ChatbotService and public_answer;
anonymous auth/empty Events fixture only, no DB/account/Production traffic or external inference.
Fixture transport was corrected during setup (internal Answer projection initially failed safe,
then actual public adapter used). No application transport workaround introduced.
No physical mobile keyboard/safe-area hardware or screen-reader acceptance claimed.
Desktop floating panel overlays nearby page content by design; launcher remains separate from
navigation. No persistent page layout shifts added. Do not treat local acceptance as deployment.

## Review and preservation
Local UI review server http://127.0.0.1:5204/ uses this worktree; API proxy stays127.0.0.1:8064.
Open launcher and switch EN/DE. Servers retained for owner review; no external resource needed.
Ignored loopback fixture script lives at original workspace .local/chatbot-design-fixture.py.
Screenshots live outside Git in the existing visualization folder:
chatbot-redesign-desktop-final.png, chatbot-redesign-narrow-final.png and EN/DE width variants.
All original worktrees/unpublished commits preserved. This task commits only scoped source,
tests/localization and concise control-plane knowledge. No push or deployment; STOP.
