# Events Recap and Explore More UI — local review, 2026-11-04

Task: FE-RECAP-EDITORIAL-001. Status: LOCAL COMPLETE — OWNER VISUAL REVIEW PENDING.
Branch: `codex/recap-editorial-ui`, based on deployed upload fix
`7176e09a62b540f3e53ad3f9da68657bb489d1df`. No push, merge, deployment or Production data access.

## UI changes

Explore More now has equal-height desktop split cards with pastel green/peach surfaces,
editorial headings, prominent 44px CTAs, subtle hover feedback and reserved image space.
Tablet cards stack their text and visual; narrow mobile cards use natural independent heights.
The Recap card shares the public gallery query key `['recaps', 1, '']` and 30-second freshness.
It uses the first published Recap in the existing API's canonical newest-event-first order,
selects its Admin thumbnail (or first photo), and reuses the existing signed-media component.
It respects the public Events flag. No new endpoint, contract or sorting assumption was added.
Empty/missing-photo/list failure/image failure retain an illustrated memory-card fallback.
The optional renderer fallback does not alter existing signing, lazy loading or retry behavior.

The Merchandise card reuses the existing Lucide shirt/bag artwork, extracted unchanged into a
shared decorative component. Coming Soon remains prominent; no purchase flow was introduced.
All labels use existing EN/DE translations. No new assets, dependencies or expensive animation.

Recap Details now renders each photo exactly once in Full Photo Gallery. The redundant first-five
Highlights section and its exclusively-used frontend styles were removed; translations retained.
The header/eyebrow/date are centered in a 1000px column; multiline description/editorial copy stays
left aligned in a centered 760px column. The centered gallery remains 1200px maximum with 3/2/1
columns. Existing order, captions, responsive images, media fallback, lightbox, keyboard next/previous,
Escape/focus restoration and Admin preview usage remain intact.

## Frontend files

- `apps/web/src/components/landing/events-explore-more.tsx`
- `apps/web/src/components/landing/events-explore-more.test.tsx`
- `apps/web/src/styles/landing.css`
- `apps/web/src/features/recaps/recap-story.tsx`
- `apps/web/src/features/recaps/recap-story.test.tsx`
- `apps/web/src/features/recaps/recap-photo.tsx`
- `apps/web/src/features/recaps/recaps.css`
- `apps/web/src/features/merchandise/merchandise-artwork.tsx`
- `apps/web/src/pages/public/community-coming-soon-page.tsx`

## Focused verification

47 tests PASS / 7 files: Explore More routes/Coming Soon/localization, latest thumbnail/first-photo
fallback, shared cache/no duplicate list request, empty/outage/broken-image fallback; detail header,
multiline copy, no Highlights, 12 ordered photos/captions in EN/DE, lightbox navigation/focus; existing
Landing/Merchandise/public gallery and Admin upload/publication regressions.

Affected ESLint and Prettier PASS. TypeScript and Production build PASS with public Events enabled;
default-disabled build also passed earlier. Existing chunk-size advisory remains. Existing demo
exclusion PASS (16 generated script/HTML files, 10 forbidden markers); additional exact synthetic
review title/banner exclusion PASS. An initial generic German phrase matched an existing approved
translation; checking unique full fixture strings correctly confirms no fixture leakage.
No unrelated full local test suites or hosted CI were run.

Local browser verification uses the actual changed components with explicitly synthetic cached
Recaps and existing approved community/campus images, in an ignored loopback-only harness. These
are not hardcoded application records. No Production session, upload, media mutation or data fetch.

EN/DE x cards/detail x 1440/768/390/320 = 16 measured cases, all without horizontal overflow.
Header center/copy left, 760px description, gallery columns 3/2/1 and six complete fixture photos
verified. Desktop/tablet cards have equal heights; mobile avoids forced empty space. Desktop,
tablet and narrow screenshots inspected; long German title and emoji wrap without clipping.
Native browser lightbox on 320px DE: next/previous keys, Escape and opener focus restored.
Links have 44px targets and visible keyboard focus. Reduced-motion emulation yields zero-second
card transitions; emulation reset. No full automated accessibility audit is claimed.

Protected-path comparison to base PASS: backend, migrations, Supabase, CI/runtime configuration,
lockfiles, auth, all Admin upload files, Recap API client, Event Slider and live Events section
unchanged. Production backup remains DEFERRED — OWNER-ACCEPTED RISK; previous real-data restore
waiver retained, no backup/recovery PASS.

## Owner review

Local preview: http://127.0.0.1:5194/.local/ui-review.html
Details: http://127.0.0.1:5194/.local/ui-review.html?view=detail
German: append `&lang=de` to Details or `?lang=de` to the card preview.
Empty state: append `?empty=1` to the card preview.
Open/refresh a preview link to reset synthetic data and media cache. The fixture entry is ignored
and is absent from Production builds. It is a design preview, not authenticated API acceptance.

Screenshots and layout-measurements.json are in the primary workspace's ignored
`.local/recap-editorial-review/` folder, including cards-1440-en.png, cards-768-de.png,
detail-320-de.png and lightbox-320-de.png.

Owner acceptance pending. Local commit only. Do not push, merge into main, deploy or change
Production without a new explicit release instruction. Existing upload acceptance remains a
separate pending Production operation; this task does not authorize it.
