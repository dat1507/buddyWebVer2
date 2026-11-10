# EVENT-SLIDER-VISIBILITY-001 — Kawazo visibility diagnosis

**Status:** DONE — ROOT CAUSE VERIFIED / UPCOMING-ONLY CONTRACT RETAINED
**Track:** events
**Assigned:** 2026-11-10

Investigated the owner-reported End Date edit and republish using read-only Production HTTP
and isolated PostgreSQL. Added focused tests for extension and clearing without an editorial
transition. The current contract excludes scheduled Events with a past Start Date.

[Cause, reproduction and release boundary](../../project-knowledge/frontend/EVENT_SLIDER_VISIBILITY_2026-11-10.md).
