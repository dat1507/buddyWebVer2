# FE-DEMO-002

**Control-plane status:** DONE / PRESERVED
**Track:** frontend
**Priority:** P1
**Dependencies (latest extracted):** FE-DEMO-001, FE-FIX-002

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 1923-1936

#### FE-DEMO-002 — Accessible Demo Video Dialog

**Status**: Completed (✅)

- Implement the dialog as an isolated Landing component without creating a new route.
- Mount/load video only after an explicit User action; use native controls and `playsInline`; pause and reset on every close.

**Implementation Notes**:
- Added a portal-based `DemoVideoDialog` controlled through `open` and `onOpenChange`, leaving trigger ownership to FE-DEMO-003.
- The MP4 is mounted only while the dialog is open, uses native controls, `playsInline`, metadata-only preload, the approved WebP poster, and no autoplay or captions track.
- Added localized EN/DE dialog title, description, media label, close action, loading status, and error fallback.
- Implemented close button, backdrop click, Escape, keyboard focus containment and return, body scroll locking, responsive viewport-constrained sizing, and cleanup that pauses and resets playback to the beginning.
- Added seven component tests covering lazy media mounting, playback attributes, every close path, focus management, scroll restoration, media cleanup, loading/error states, and German accessibility copy.


## Cross-reference occurrences outside extracted headings

- Legacy line 1272: | FE-DEMO-002 | Create an accessible responsive Demo Video dialog | FE-DEMO-001, FE-FIX-002 | P1 |
- Legacy line 1273: | FE-DEMO-003 | Connect Watch Demo to the video dialog | FE-DEMO-002 | P1 |
- Legacy line 1920: - Kept both assets in Vite's public directory so FE-DEMO-002 can reference stable \`/media/...\` URLs without adding the MP4 to the JavaScript module graph.
- Legacy line 4237: Done:    FE-DEMO-002     Create accessible Demo Video dialog [completed 2026-09-10]
