# PROFILE-V2-002

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** PROFILE-V2-001, FE-029; Frontend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7269-7302

#### PROFILE-V2-002 — Locked `student_type` frontend UX

- **Status:** **Done 2026-09-30.** The authenticated own-profile DTO now exposes only the
  privacy-safe `student_type_locked` capability derived from authoritative ACTIVE Match
  persistence. Profile edit renders the persisted type, disables both type choices and associates
  an inline explanation with the field whenever the capability is true. Other profile fields and
  Save remain available; same-value serialization continues to use the established backend update
  and optimistic-version contract. Onboarding remains unchanged and editable because this lock UX
  is scoped to the existing-profile editor.
- **Implementation:** The client validates the capability in the own-profile schema and recognizes
  `STUDENT_TYPE_LOCKED_ACTIVE_MATCH` only as an allowlisted 409 reason from `/profile`; unknown
  bodies and other endpoints remain sanitized. A stale editable page receiving that reason locks
  the type immediately, restores the last persisted type, refetches profile/readiness and preserves
  unrelated local form edits. Ordinary stale-version conflicts retain the prior explicit reload
  flow and are not misclassified. English and German copy explains that only student type is locked;
  disabled semantics, associated descriptions, visible icon-plus-text feedback and responsive
  wrapping make the state keyboard/screen-reader/mobile safe without relying on color or tooltip.
- **Verification:** **29 targeted frontend transport/component/onboarding tests** and **93 related
  profile/onboarding/PREF/auth/matching regressions** pass; the full frontend suite passes **565
  tests across 57 files**. Full Prettier, ESLint, TypeScript, production build and production
  dependency audit (zero vulnerabilities) pass. The minimal backend DTO coverage passes **66
  targeted tests** and the full backend suite passes **1015 tests / 26 configured live skips**;
  Ruff, strict mypy (**195 source files**), pip consistency, package build, locked dependency audit
  (zero known vulnerabilities), Alembic history/single head/autogenerate drift and Docker Compose
  validation pass. No migration is required; Alembic head remains
  `0013_active_match_persistence`.
- **Purpose:** Explain the confirmed backend restriction before a user submits an impossible edit.
- **Scope / likely files:** own-profile query/schema/client, profile edit field, help/error copy and locales; consume backend lock state/reason and conflict code.
- **Dependencies / ownership:** PROFILE-V2-001, FE-029; Frontend.
- **Security:** disabled/readonly UI is advisory only; submit handling must display the backend conflict and refetch after stale-tab/race responses.
- **Acceptance / DoD:** a user with at least one ACTIVE Match sees the type field locked with an accessible explanation that current Buddies require opposite types; users without an ACTIVE Match can edit it; no Unmatch action or promise of automatic migration is shown.
- **Tests/gates:** component/a11y/integration tests cover unlocked, locked, one/many Buddy-equivalent state, stale unlocked tab receiving `STUDENT_TYPE_LOCKED_ACTIVE_MATCH`, reload and localized explanation.
- **Non-goals:** enforcing security in the browser or adding relationship-ending controls.


## Cross-reference occurrences outside extracted headings

- Legacy line 6866: | PROFILE-V2-002 (**Done 2026-09-30**) | Locked \`student_type\` profile UX | PROFILE-V2-001, FE-029 | Disabled field, explanation and stale-conflict handling | Component/a11y/integration tests |
- Legacy line 8168: BUDDY-001 → PROFILE-V2-001 → PROFILE-V2-002
- Legacy line 8200: Clarification of the intertwined invitation path: \`BUDDY-001\` starts after REC-002; \`PROFILE-V2-001\` and \`CHAT-001\` then branch from it and both must finish before INV-005. INV-001/002/003/004 proceed in parallel with that persistence branch. INV-005 then uses the shared profile/participant locking policy and atomically creates the opposite-type ACTIVE Match and its one conversation. \`PROFILE-V2-002\` may proceed as soon as the backend profile contract is stable.
- Legacy line 8208: 4. Complete \`BUDDY-001\`, then \`PROFILE-V2-001\`, \`PROFILE-V2-002\` and \`CHAT-001\`; \`INV-008\` may proceed once \`INV-003\` is complete.
- Legacy line 8224: Final integration convergence: EMAIL-005 + PREF-004 + PROFILE-V2-002 + REC-004 + INV-007/008/009 + BUDDY-003 + CHAT-004/005 + ADMIN-V2-002 + SEM-007 + OPS-003 must all pass before ACCEPT-001.
- Legacy line 8244: The **second mandatory staging milestone** is after the complete user vertical slice **through PROFILE-V2-002 and CHAT-004 plus INV-008/009 and ADMIN-V2-002**. It validates two real verified users from recommendation through invitation/email/Accept/Current Buddies/chat, including exact invitation boundaries and the post-Accept type lock. Staging remains incomplete until **SEM-007 + CHAT-005 + OPS-003** and ACCEPT-001 prove reset/backup/restore/blocking and retention.
- Legacy line 8294: | **STAGING** | **OPS-002 AND OPS-003 DONE** | Early infrastructure, restore/migration, Edge/Cron A–F, real verification acceptance and primary/backup alert routing passed. The implemented PROFILE-V2-002 + CHAT-004 + INV-008/009 + ADMIN-V2-002 vertical slice still needs staging acceptance; release-candidate staging requires SEM-007 and ACCEPT-001. |
