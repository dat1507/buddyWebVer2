# FE-LANDING-FOOTER-001 — Minimal Branding Footer

**Assigned:** 2026-10-17 (Asia/Saigon), owner pasted request.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.

Replace Footer Quick Links and Support/International Office with a two-column branding and
Get in Touch layout. Preserve logo proportions, existing Facebook/Instagram URLs/icons, dark
background, orange accents, `#contact`, dynamic year and localized copyright/EN-DE availability.
Use the owner's exact EN descriptions and natural DE copy; Contact Us links to
`mailto:vgubuddy@vgu.edu.vn` with an email icon. No form, API or extra contact channel.

Focused files: Footer source/new focused tests, EN/DE footer locales, Landing assembly tests
and frontend knowledge. Validate removed links, retained resources/Navbar, safe social links,
mailto, keyboard focus, contrast, reduced motion and responsive layout, focused tests,
TypeScript, ESLint, Prettier and production build. Initial main clean at `6685bc9`.
Commit code/tests/knowledge locally; no push, Preview/Production deployment or backend/data change.

## Verified outcome — 2026-10-17

Shared PublicLayout Footer now has branding/socials and Get in Touch columns at 768px+,
stacking below that breakpoint. Quick Links and Support/International Office are removed only
from Footer; Navbar and the International Office resource card are unchanged. Existing bundled
logo remains 48×48; exact Facebook/Instagram URLs and icon styling remain, with explicit
`noopener noreferrer` and reduced-motion-safe transitions. Contact Us / Kontaktiere uns uses
`mailto:vgubuddy@vgu.edu.vn`; the email is also visible. No mail was sent or contact form added.
EN/DE branding/contact copy updated; dynamic year and localized availability retained. Copyright
text now uses the existing readable zinc-400 token; divider, dark background and orange focus
rings remain. Footer `#contact` has an 80px scroll margin.

Footer/Landing/Resources tests: 3 files / 19 PASS. TypeScript, affected ESLint/Prettier and
production build PASS; existing large-chunk advisory. Brave EN/DE at 1440×1000, 768×1000 and
390×1000: two/two/one columns, zero horizontal overflow, decoded 48px logo, 44px social/contact
links. Tab moves Facebook → Instagram → Contact Us with visible orange rings. Reduced-motion
social transition properties are none. Exact mailto/social targets checked without opening an
email client or sending mail. Local API bootstrap warning persists outside Footer; no account
or Production acceptance. See [validation](../validation.md). Local commit only.
