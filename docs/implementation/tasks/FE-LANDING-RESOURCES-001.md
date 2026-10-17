# FE-LANDING-RESOURCES-001 — Campus Resources grid

**Assigned:** 2026-10-17 (Asia/Saigon), owner pasted task contract.
**Status:** DONE — LOCAL VERIFIED / NOT DEPLOYED.

## Contract

Replace Outstanding Benefits with Campus Resources, retaining `#features` and navbar navigation.
Use EN/DE and shared Card/Typography styling consistent with About. Show five resources: Events
Recap, Library, Sports Hall, International Office and Dormitory Service; remove Merchandise from
this section. Desktop 3+2 centered, tablet two columns, mobile one column. Preserve keyboard focus,
contrast, touch targets and reduced motion; change no other product behavior.

Events Recap: **UI prepared — functionality pending**; no route or action. Verified official
resources open new tabs with `noopener noreferrer`. All four destinations were supplied/confirmed by the owner on 2026-10-17; no URL inputs remain.
International Office also verified through the official site. External destination availability
was not independently checked for the other three owner-confirmed links.

## Focused sources and verification

- `apps/web/src/components/landing/benefits-grid.tsx` and focused test.
- `apps/web/src/components/layout/navbar.tsx` and focused test (anchor remains unchanged).
- `apps/web/src/locales/{en,de}/common.json` and Landing assembly test.
- Shared Card/Typography, About styling and existing hash scroll behavior.
- Focused tests, TypeScript, ESLint, Prettier, production build and local responsive/anchor checks.
- Update control plane, handoff, task index, validation and frontend project knowledge together.

## Evidence

Initial worktree clean on `main` at `ce6efeb`. Implemented five equal-height icon cards,
localized navbar/footer labels and section copy, desktop centered 3+2, tablet 2-column and mobile
1-column grid. Shared Card/Typography and About colors/padding retained; old bullet lists removed.
Landing hash-mount handling now includes `#features` alongside `#about` to support direct refresh.

| Resource             | Destination / behavior                                           |
| -------------------- | ---------------------------------------------------------------- |
| Events Recap         | UI prepared — functionality pending; no action, route or backend |
| Library              | https://library.vgu.edu.vn/                                      |
| Sports Hall          | https://vgu.edu.vn/sports-complex                                |
| International Office | https://vgu.edu.vn/international-office                          |
| Dormitory Service    | https://dorm.vgu.edu.vn/                                         |

All four links use new tabs, `noopener noreferrer`, localized accessible names/new-tab notice,
visible focus rings and 44px minimum height. Hover border/shadow transitions disable under reduced
motion. No dependencies, heavy assets, Event, auth, Dashboard, backend or database changes.

Verification: see [dated validation](../validation.md). Brave local checks at 1440×1000,
768×1024 and 390×844 confirmed 3+2/2/1 columns and zero horizontal overflow. EN/DE content
and reduced-motion computed transition-property `none` pass; direct refresh places the section
at about 80px, below the 65px navbar. The unrelated local auth bootstrap connection warning
remains; no authenticated session or Production runtime was used.
Owner authorizes a local commit; no push, deployment or Production writes.
