# Task index

**Generated:** 2026-10-10  **Task IDs:** 215

Use the lightweight plan for current priority, then open only the selected task extract. Extracts
preserve all matching contract sections and cross-references from the legacy plan. `SUPERSEDED` and
`RECONTRACT REQUIRED` entries are not executable.

| Task | Status | Priority | Track | Dependencies / source note |
| --- | --- | --- | --- | --- |
| [`ACCEPT-001`](tasks/ACCEPT-001.md) | OPEN / POST-DEPLOY HARDENING | - | release-operations | EMAIL/PREF/PROFILE/REC/INV/BUDDY/CHAT/ADMIN V2 tasks, SEM-007, CHAT-005, OPS-003; QA + Product + Engineering + Operations. |
| [`ACCEPT-EVENT-001`](tasks/ACCEPT-EVENT-001.md) | DONE — FLAG-OFF PRODUCTION SMOKE PASS | P0 | release-operations | Local A–E, Quality Gate E, rollback preflight, `e2ef4c0` rollout and read-only Production smoke passed; separate data/launch approval remains. |
| [`ADMIN-001`](tasks/ADMIN-001.md) | DONE / PRESERVED | P0 | admin | FE-005, AUTH-006 — both DONE; shared Card/Typography/buttons and actual ADMIN RoleGuard acceptance verified. |
| [`ADMIN-002`](tasks/ADMIN-002.md) | DONE / PRESERVED | P0 | admin | ADMIN-001 — DONE; source shell, tests and accepted Git/CI evidence verified. |
| [`ADMIN-003`](tasks/ADMIN-003.md) | DONE / PRESERVED | P0 | admin | ADMIN-001 — DONE; guarded shell, tests and accepted Git/CI evidence verified. ADMIN-002 is also already on main but is not a declared dependency. |
| [`ADMIN-004`](tasks/ADMIN-004.md) | DONE / PRESERVED | P0 | admin | FE-005 — DONE; design-system Button/Card/Typography/theme source and existing regression evidence verified. FE-004 shadcn configuration/Radix Slot is also present but is not a d... |
| [`ADMIN-005`](tasks/ADMIN-005.md) | DONE / PRESERVED | P0 | admin | FE-004 — DONE; shadcn configuration, shared Button primitive and modal-isolation convention verified. |
| [`ADMIN-006`](tasks/ADMIN-006.md) | IMPLEMENTED / AUTOMATED PASS — STAGING UI GATE PENDING | P0 | admin | `ADMIN-004`, `EVT-006`, `EVT-009`. |
| [`ADMIN-007`](tasks/ADMIN-007.md) | IMPLEMENTED / AUTOMATED PASS — STAGING UI GATE PENDING | P0 | admin | `ADMIN-006`, `EVT-011`. |
| [`ADMIN-008`](tasks/ADMIN-008.md) | IMPLEMENTED / AUTOMATED PASS — STAGING UI GATE PENDING | P0 | admin | `ADMIN-007`. |
| [`ADMIN-009`](tasks/ADMIN-009.md) | IMPLEMENTED / AUTOMATED PASS — STAGING UI GATE PENDING | P0 | admin | `ADMIN-008`, `EVT-009`. |
| [`ADMIN-010`](tasks/ADMIN-010.md) | PLANNED / BACKLOG | P0 | admin | ADMIN-005, ADMIN-006, EVT-009 |
| [`ADMIN-011`](tasks/ADMIN-011.md) | PLANNED / BACKLOG | P1 | admin | ADMIN-006, EVT-007 |
| [`ADMIN-012`](tasks/ADMIN-012.md) | DONE / PRESERVED | P0 | admin | ADMIN-004, BE-013 |
| [`ADMIN-013`](tasks/ADMIN-013.md) | DONE / PRESERVED | P0 | admin | ADMIN-012 |
| [`ADMIN-014`](tasks/ADMIN-014.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | admin | ADMIN-003, MATCH-013 |
| [`ADMIN-015`](tasks/ADMIN-015.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | admin | ADMIN-014, MATCH-008 |
| [`ADMIN-016`](tasks/ADMIN-016.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | admin | ADMIN-015, MATCH-013, MATCH-014 |
| [`ADMIN-017`](tasks/ADMIN-017.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | admin | ADMIN-016, MATCH-014 |
| [`ADMIN-018`](tasks/ADMIN-018.md) | SUPERSEDED / DO NOT IMPLEMENT | P1 | admin | ADMIN-014, MATCH-013 |
| [`ADMIN-019`](tasks/ADMIN-019.md) | RECONTRACT REQUIRED | - | admin | See preserved extract |
| [`ADMIN-EVT-001`](tasks/ADMIN-EVT-001.md) | PLANNED / BACKLOG | P0 | events | ADMIN-008, EVT-013 |
| [`ADMIN-EVT-002`](tasks/ADMIN-EVT-002.md) | PLANNED / BACKLOG | P1 | events | ADMIN-EVT-001, EVT-011 |
| [`ADMIN-SLIDER-001`](tasks/ADMIN-SLIDER-001.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | events | ADMIN-004, EVS-006 |
| [`ADMIN-SLIDER-002`](tasks/ADMIN-SLIDER-002.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | events | ADMIN-SLIDER-001, EVS-003 |
| [`ADMIN-SLIDER-003`](tasks/ADMIN-SLIDER-003.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | events | ADMIN-005, ADMIN-SLIDER-001 |
| [`ADMIN-SLIDER-004`](tasks/ADMIN-SLIDER-004.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | events | ADMIN-SLIDER-001, EVS-006 |
| [`ADMIN-V2-001`](tasks/ADMIN-V2-001.md) | DONE / PRESERVED | - | admin | INV-006, BUDDY-002, existing AUTH-018/EVT-008; Backend. |
| [`ADMIN-V2-002`](tasks/ADMIN-V2-002.md) | DONE / PRESERVED | - | admin | ADMIN-V2-001, ADMIN-003/004; Frontend. |
| [`AUTH-001`](tasks/AUTH-001.md) | DONE / PRESERVED | P0 | auth-email | FE-005, FE-006 |
| [`AUTH-002`](tasks/AUTH-002.md) | DONE / PRESERVED | P0 | auth-email | FE-005, FE-006 |
| [`AUTH-003`](tasks/AUTH-003.md) | DONE / PRESERVED | P0 | auth-email | FE-005, FE-006 |
| [`AUTH-004`](tasks/AUTH-004.md) | DONE / PRESERVED | P0 | auth-email | FE-001, AUTH-ARCH-001 (both completed). |
| [`AUTH-005`](tasks/AUTH-005.md) | DONE / PRESERVED | P0 | auth-email | AUTH-004, FE-006; current AUTH-021 bootstrap integration is reused. |
| [`AUTH-006`](tasks/AUTH-006.md) | DONE / PRESERVED | P0 | auth-email | AUTH-005; reuses AUTH-004 sanitized role and AUTH-021 verified bootstrap. |
| [`AUTH-007`](tasks/AUTH-007.md) | DONE / PRESERVED | P0 | auth-email | BE-006 |
| [`AUTH-008`](tasks/AUTH-008.md) | DONE / PRESERVED | P0 | auth-email | AUTH-007 |
| [`AUTH-009`](tasks/AUTH-009.md) | DONE / PRESERVED | P0 | auth-email | AUTH-008 |
| [`AUTH-010`](tasks/AUTH-010.md) | DONE / PRESERVED | P0 | auth-email | BE-001 |
| [`AUTH-011`](tasks/AUTH-011.md) | DONE / PRESERVED | P0 | auth-email | BE-001, AUTH-ARCH-001 |
| [`AUTH-011A`](tasks/AUTH-011A.md) | DONE / PRESERVED | P0 | auth-email | BE-001, AUTH-ARCH-001 |
| [`AUTH-012`](tasks/AUTH-012.md) | DONE / PRESERVED | P0 | auth-email | AUTH-008, AUTH-010, AUTH-011 |
| [`AUTH-013`](tasks/AUTH-013.md) | DONE / PRESERVED | P0 | auth-email | AUTH-012, AUTH-011A |
| [`AUTH-014`](tasks/AUTH-014.md) | DONE / PRESERVED | P0 | auth-email | AUTH-012, AUTH-011A |
| [`AUTH-015`](tasks/AUTH-015.md) | DONE / PRESERVED | P0 | auth-email | AUTH-011, AUTH-011A |
| [`AUTH-016`](tasks/AUTH-016.md) | DONE / PRESERVED | P0 | auth-email | AUTH-017 |
| [`AUTH-017`](tasks/AUTH-017.md) | DONE / PRESERVED | P0 | auth-email | AUTH-011, AUTH-009 |
| [`AUTH-018`](tasks/AUTH-018.md) | DONE / PRESERVED | P0 | auth-email | AUTH-017 |
| [`AUTH-019`](tasks/AUTH-019.md) | DONE / PRESERVED | P0 | auth-email | AUTH-008, AUTH-010 |
| [`AUTH-020`](tasks/AUTH-020.md) | DONE / PRESERVED | P0 | auth-email | BE-001; current AUTH-013/014/015/016 identity and transaction contracts. |
| [`AUTH-021`](tasks/AUTH-021.md) | DONE / PRESERVED | P0 | auth-email | AUTH-004, AUTH-013, AUTH-014, AUTH-015, AUTH-016, AUTH-024 |
| [`AUTH-022`](tasks/AUTH-022.md) | DONE / PRESERVED | P0 | auth-email | AUTH-021, AUTH-006 (complete on this branch). |
| [`AUTH-023`](tasks/AUTH-023.md) | DONE / PRESERVED | P0 | auth-email | AUTH-021, AUTH-006 (complete on this branch). |
| [`AUTH-024`](tasks/AUTH-024.md) | DONE / PRESERVED | P0 | auth-email | AUTH-015, AUTH-017, AUTH-011A |
| [`AUTH-025`](tasks/AUTH-025.md) | PLANNED / BACKLOG | P1 | auth-email | AUTH-024, AUTH-010 |
| [`AUTH-ARCH-001`](tasks/AUTH-ARCH-001.md) | DONE / PRESERVED | P0 | auth-email | FE-HYGIENE-002 |
| [`AUTH-V2-001`](tasks/AUTH-V2-001.md) | DONE / PRESERVED | - | auth-email | EMAIL-001, BE-016; Backend contract + Frontend integration. |
| [`BE-001`](tasks/BE-001.md) | DONE / PRESERVED | P0 | backend-foundation | — |
| [`BE-002`](tasks/BE-002.md) | DONE / PRESERVED | P0 | backend-foundation | BE-001 |
| [`BE-003`](tasks/BE-003.md) | DONE / PRESERVED | P0 | backend-foundation | BE-001 |
| [`BE-004`](tasks/BE-004.md) | DONE / PRESERVED | P0 | backend-foundation | BE-003 |
| [`BE-005`](tasks/BE-005.md) | DONE / PRESERVED | P0 | backend-foundation | BE-001 |
| [`BE-006`](tasks/BE-006.md) | DONE / PRESERVED | P0 | backend-foundation | BE-003 |
| [`BE-007`](tasks/BE-007.md) | DONE / PRESERVED | P0 | backend-foundation | BE-001, AUTH-ARCH-001 |
| [`BE-008`](tasks/BE-008.md) | DONE / PRESERVED | P0 | backend-foundation | AUTH-008 |
| [`BE-009`](tasks/BE-009.md) | DONE / PRESERVED | P0 | backend-foundation | BE-008 |
| [`BE-010`](tasks/BE-010.md) | DONE / PRESERVED | P0 | backend-foundation | BE-008, BE-009, AUTH-009, BE-004 |
| [`BE-011`](tasks/BE-011.md) | DONE / PRESERVED | P0 | backend-foundation | BE-010 |
| [`BE-012`](tasks/BE-012.md) | DONE / PRESERVED | P0 | backend-foundation | BE-011, AUTH-017, AUTH-011A |
| [`BE-013`](tasks/BE-013.md) | DONE / PRESERVED | P0 | backend-foundation | BE-011, AUTH-018, EVT-008 |
| [`BE-014`](tasks/BE-014.md) | DONE / PRESERVED | P0 | backend-foundation | BE-010, BE-012, EVS-003 |
| [`BE-015`](tasks/BE-015.md) | DONE / PRESERVED | P0 | backend-foundation | BE-009, BE-012 |
| [`BE-016`](tasks/BE-016.md) | DONE / PRESERVED | P0 | backend-foundation | BE-012, BE-014, BE-015 |
| [`BUDDY-001`](tasks/BUDDY-001.md) | DONE / PRESERVED | - | buddy-v2 | REC-002; Database + Backend. |
| [`BUDDY-002`](tasks/BUDDY-002.md) | DONE / PRESERVED | - | buddy-v2 | BUDDY-001, INV-005, AUTH-V2-001; Backend. |
| [`BUDDY-003`](tasks/BUDDY-003.md) | DONE / PRESERVED | - | buddy-v2 | BUDDY-002, INV-007; Frontend. |
| [`CHAT-001`](tasks/CHAT-001.md) | DONE / PRESERVED | - | buddy-v2 | BUDDY-001; Database + Backend. |
| [`CHAT-002`](tasks/CHAT-002.md) | DONE / PRESERVED | - | buddy-v2 | CHAT-001, AUTH-V2-001; Backend. |
| [`CHAT-003`](tasks/CHAT-003.md) | DONE / PRESERVED | - | buddy-v2 | CHAT-002, OPS-001; Backend + Infrastructure. |
| [`CHAT-004`](tasks/CHAT-004.md) | DONE / PRESERVED | - | buddy-v2 | CHAT-003, BUDDY-003; Frontend. |
| [`CHAT-005`](tasks/CHAT-005.md) | DONE / PRESERVED | - | buddy-v2 | CHAT-002, OPS-001; Backend + Infrastructure. |
| [`EMAIL-001`](tasks/EMAIL-001.md) | DONE / PRESERVED | - | auth-email | AUTH-008/009; Backend + Database. |
| [`EMAIL-001A`](tasks/EMAIL-001A.md) | DONE / PRESERVED | - | auth-email | EMAIL-001; Backend. |
| [`EMAIL-002`](tasks/EMAIL-002.md) | DONE / PRESERVED | - | auth-email | EMAIL-001A, MAIL-001, AUTH-020; Backend. |
| [`EMAIL-003`](tasks/EMAIL-003.md) | DONE / PRESERVED | - | auth-email | EMAIL-001A; Backend + Database. |
| [`EMAIL-004`](tasks/EMAIL-004.md) | DONE / PRESERVED | - | auth-email | EMAIL-001/002, existing sessions; Backend + Database. |
| [`EMAIL-005`](tasks/EMAIL-005.md) | DONE / PRESERVED | - | auth-email | EMAIL-002..004, AUTH-021; Frontend. |
| [`EVS-001`](tasks/EVS-001.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | events | BE-006, AUTH-008, EVT-001 |
| [`EVS-002`](tasks/EVS-002.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | events | EVS-001, EVT-003 |
| [`EVS-003`](tasks/EVS-003.md) | DONE / PRESERVED | P0 | events | BE-004, AUTH-018, AUTH-011A |
| [`EVS-004`](tasks/EVS-004.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | events | EVS-002, EVS-003, EVT-009 |
| [`EVS-005`](tasks/EVS-005.md) | IMPLEMENTED / AUTOMATED PASS — STAGING FRESHNESS GATE PENDING | P0 | events | `EVT-005`, `EVT-011`. |
| [`EVS-006`](tasks/EVS-006.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | events | EVS-004, AUTH-018 |
| [`EVS-007`](tasks/EVS-007.md) | DONE — SUPPORTED-RUNTIME REGRESSION PASS | P0 | events | Python 3.12 full backend and Event/frontend/security gates PASS. |
| [`EVT-001`](tasks/EVT-001.md) | DONE / PRESERVED | P0 | events | BE-006, AUTH-008 |
| [`EVT-002`](tasks/EVT-002.md) | DONE / PRESERVED | P0 | events | EVT-001 |
| [`EVT-003`](tasks/EVT-003.md) | DONE / PRESERVED | P0 | events | EVT-001, EVT-002, EVT-010, AUTH-009, BE-004 |
| [`EVT-004`](tasks/EVT-004.md) | DONE / PRESERVED | P0 | events | EVT-003 |
| [`EVT-005`](tasks/EVT-005.md) | IMPLEMENTED / AUTOMATED PASS — STAGING QUERY GATE PENDING | P0 | events | `EVT-004`, `EVT-010`, `EVS-003`, `AUTH-017` and migration `0007` DONE. |
| [`EVT-006`](tasks/EVT-006.md) | IMPLEMENTED / AUTOMATED PASS — STAGING RBAC GATE PENDING | P0 | events | `EVT-004`, `EVT-005`, `AUTH-018`, `AUTH-011A`, `EVT-008`. |
| [`EVT-007`](tasks/EVT-007.md) | PLANNED / BACKLOG | P1 | events | EVT-002, AUTH-017 |
| [`EVT-008`](tasks/EVT-008.md) | DONE / PRESERVED | P0 | events | AUTH-009 |
| [`EVT-009`](tasks/EVT-009.md) | IMPLEMENTED / AUTOMATED PASS — STAGING MUTATION GATE PENDING | P0 | events | `EVT-006`, `EVT-008`. |
| [`EVT-010`](tasks/EVT-010.md) | DONE / PRESERVED | P0 | events | EVT-001 |
| [`EVT-011`](tasks/EVT-011.md) | IMPLEMENTED / AUTOMATED PASS — STORAGE/STAGING GATE PENDING | P0 | events | `EVT-010`, `EVS-003`, `EVT-006`, `EVT-009`. |
| [`EVT-012`](tasks/EVT-012.md) | PLANNED / BACKLOG | P0 | events | EVT-003, EVT-010 |
| [`EVT-013`](tasks/EVT-013.md) | PLANNED / BACKLOG | P0 | events | EVT-012, EVT-011 |
| [`FE-001`](tasks/FE-001.md) | DONE / PRESERVED | P0 | frontend | — |
| [`FE-002`](tasks/FE-002.md) | DONE / PRESERVED | P0 | frontend | FE-001 |
| [`FE-003`](tasks/FE-003.md) | DONE / PRESERVED | P0 | frontend | FE-001 |
| [`FE-004`](tasks/FE-004.md) | DONE / PRESERVED | P0 | frontend | FE-003 |
| [`FE-005`](tasks/FE-005.md) | DONE / PRESERVED | P0 | frontend | FE-003 |
| [`FE-006`](tasks/FE-006.md) | DONE / PRESERVED | P0 | frontend | FE-001 |
| [`FE-007`](tasks/FE-007.md) | DONE / PRESERVED | P0 | frontend | FE-001 |
| [`FE-008`](tasks/FE-008.md) | DONE / PRESERVED | P0 | frontend | FE-001 |
| [`FE-009`](tasks/FE-009.md) | DONE / PRESERVED | P0 | frontend | FE-001 |
| [`FE-010`](tasks/FE-010.md) | DONE / PRESERVED | P0 | frontend | FE-009 |
| [`FE-011`](tasks/FE-011.md) | DONE / PRESERVED | P0 | frontend | FE-005, FE-006, FE-009 |
| [`FE-012`](tasks/FE-012.md) | DONE / PRESERVED | P0 | frontend | FE-005 |
| [`FE-013`](tasks/FE-013.md) | DONE / PRESERVED | P0 | frontend | FE-005 |
| [`FE-014`](tasks/FE-014.md) | DONE / PRESERVED | P0 | frontend | FE-005, FE-007, FE-009 |
| [`FE-014B`](tasks/FE-014B.md) | IMPLEMENTED / AUTOMATED PASS — STAGING LIVE GATE PENDING | P0 | events | `FE-014`, `EVS-005`, `FE-031`, `ADMIN-009`. |
| [`FE-015`](tasks/FE-015.md) | DONE / PRESERVED | P0 | frontend | FE-005 |
| [`FE-016`](tasks/FE-016.md) | DONE / PRESERVED | P0 | frontend | FE-005 |
| [`FE-017`](tasks/FE-017.md) | DONE / PRESERVED | P0 | frontend | FE-005 |
| [`FE-018`](tasks/FE-018.md) | DONE / PRESERVED | P0 | frontend | FE-005 |
| [`FE-019`](tasks/FE-019.md) | DONE / PRESERVED | P0 | frontend | FE-011..FE-018 |
| [`FE-020`](tasks/FE-020.md) | DONE / PRESERVED | P0 | frontend | FE-009, FE-011 |
| [`FE-021`](tasks/FE-021.md) | DONE / PRESERVED | P0 | frontend | FE-005, AUTH-006 |
| [`FE-022`](tasks/FE-022.md) | DONE / PRESERVED | P0 | frontend | FE-021 |
| [`FE-023`](tasks/FE-023.md) | DONE / PRESERVED | P0 | frontend | FE-021, FE-022, BE-012, BE-016, FE-038 |
| [`FE-024`](tasks/FE-024.md) | PLANNED / BACKLOG | P1 | frontend | FE-021, AUTH-021, AUTH-025 |
| [`FE-025`](tasks/FE-025.md) | DONE / PRESERVED | P0 | frontend | FE-021, BE-012 |
| [`FE-026`](tasks/FE-026.md) | DONE / PRESERVED | P0 | frontend | FE-025, BE-015 |
| [`FE-027`](tasks/FE-027.md) | DONE / PRESERVED | P0 | frontend | FE-026, BE-012, BE-016, FE-039 |
| [`FE-028`](tasks/FE-028.md) | DONE / PRESERVED | P0 | frontend | FE-025, BE-012, BE-014, BE-015 |
| [`FE-029`](tasks/FE-029.md) | DONE / PRESERVED | P0 | frontend | FE-028, FE-027, BE-016 |
| [`FE-030`](tasks/FE-030.md) | PLANNED / BACKLOG | P1 | events | FE-021, EVT-005 |
| [`FE-031`](tasks/FE-031.md) | IMPLEMENTED / AUTOMATED PASS — STAGING DIRECT-URL GATE PENDING | P0 | events | `FE-006`, `EVT-005`, `EVT-011`; `EVT-013` recap dependency removed. |
| [`FE-032`](tasks/FE-032.md) | PLANNED / BACKLOG | P1 | events | FE-031, EVT-007 |
| [`FE-033`](tasks/FE-033.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | frontend | FE-027, BE-012, BE-016 |
| [`FE-034`](tasks/FE-034.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | frontend | FE-033, MATCH-009 |
| [`FE-035`](tasks/FE-035.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | frontend | FE-034, MATCH-010 |
| [`FE-036`](tasks/FE-036.md) | PLANNED / BACKLOG | P1 | frontend | FE-034, MATCH-011 |
| [`FE-037`](tasks/FE-037.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | frontend | FE-034, FE-035 |
| [`FE-038`](tasks/FE-038.md) | DONE / PRESERVED | P0 | frontend | AUTH-022, AUTH-023, BE-016, FE-027 |
| [`FE-039`](tasks/FE-039.md) | DONE / PRESERVED | P0 | frontend | FE-025, BE-014 |
| [`FE-AUTH-ENTRY-001`](tasks/FE-AUTH-ENTRY-001.md) | DONE / PRESERVED | P0 | frontend | AUTH-001, AUTH-002 |
| [`FE-AUTH-ENTRY-002`](tasks/FE-AUTH-ENTRY-002.md) | DONE / PRESERVED | P0 | frontend | AUTH-001, AUTH-002 |
| [`FE-AUTH-ENTRY-003`](tasks/FE-AUTH-ENTRY-003.md) | DONE / PRESERVED | P1 | frontend | AUTH-002 |
| [`FE-CLOSEOUT-001`](tasks/FE-CLOSEOUT-001.md) | DONE / PRESERVED | P0 | frontend | FE-VERIFY-001 |
| [`FE-CLOSEOUT-002`](tasks/FE-CLOSEOUT-002.md) | DONE / PRESERVED | P0 | frontend | FE-CLOSEOUT-001 |
| [`FE-CLOSEOUT-003`](tasks/FE-CLOSEOUT-003.md) | DONE / PRESERVED | P0 | frontend | FE-CLOSEOUT-002 |
| [`FE-DEMO-001`](tasks/FE-DEMO-001.md) | DONE / PRESERVED | P1 | frontend | FE-HYGIENE-001 |
| [`FE-DEMO-002`](tasks/FE-DEMO-002.md) | DONE / PRESERVED | P1 | frontend | FE-DEMO-001, FE-FIX-002 |
| [`FE-DEMO-003`](tasks/FE-DEMO-003.md) | DONE / PRESERVED | P1 | frontend | FE-DEMO-002 |
| [`FE-EVENT-CALENDAR-001`](tasks/FE-EVENT-CALENDAR-001.md) | PLANNED / BACKLOG | P1 | events | FE-030, FE-031, FE-014B |
| [`FE-EVENT-STATIC-001`](tasks/FE-EVENT-STATIC-001.md) | DONE / PRESERVED | - | events | completed Landing/carousel foundation and the six audited project-owned posters. |
| [`FE-FIX-001`](tasks/FE-FIX-001.md) | DONE / PRESERVED | P0 | frontend | FE-HYGIENE-001 |
| [`FE-FIX-002`](tasks/FE-FIX-002.md) | DONE / PRESERVED | P0 | frontend | FE-HYGIENE-001 |
| [`FE-FIX-003`](tasks/FE-FIX-003.md) | DONE / PRESERVED | P1 | frontend | FE-FIX-002 |
| [`FE-FIX-004`](tasks/FE-FIX-004.md) | DONE / PRESERVED | P1 | frontend | FE-HYGIENE-001 |
| [`FE-FIX-005`](tasks/FE-FIX-005.md) | DONE / PRESERVED | P1 | frontend | FE-FIX-001 |
| [`FE-HYGIENE-001`](tasks/FE-HYGIENE-001.md) | DONE / PRESERVED | P0 | frontend | FE-020 |
| [`FE-HYGIENE-002`](tasks/FE-HYGIENE-002.md) | DONE / PRESERVED | P0 | frontend | FE-CLOSEOUT-003 |
| [`FE-LANDING-BG-001`](tasks/FE-LANDING-BG-001.md) | DONE — PRODUCTION VERIFIED | Phase 2 P1 | frontend | Vercel Production and direct desktop/mobile/transition verification pass. |
| [`FE-LANDING-BG-002`](tasks/FE-LANDING-BG-002.md) | DONE — PRODUCTION VERIFIED | Phase 2 corrective | frontend | `c2fbaf1`; Vercel Production and three-loop browser audit pass. |
| [`FE-PROFILE-HOME-UNI-001`](tasks/FE-PROFILE-HOME-UNI-001.md) | DEPLOYED — DISPLAY ACCEPTED / EDIT-PERSISTENCE GATES OPEN | Phase 2 P2 | profile | Owner confirmed Production display; edit/save/reload/clear/max acceptance remains. |
| [`FE-TECH-001`](tasks/FE-TECH-001.md) | DONE / PRESERVED | P2 | frontend | Frontend functional fixes |
| [`FE-VERIFY-001`](tasks/FE-VERIFY-001.md) | DONE / PRESERVED | P0 | frontend | All selected Frontend completion tasks |
| [`INV-001`](tasks/INV-001.md) | DONE / PRESERVED | - | buddy-v2 | REC-001; Database + Backend. |
| [`INV-002`](tasks/INV-002.md) | DONE / PRESERVED | - | buddy-v2 | INV-001; Backend + Infrastructure. |
| [`INV-003`](tasks/INV-003.md) | DONE / PRESERVED | - | buddy-v2 | INV-002, REC-003, MAIL-001; Backend + Database. |
| [`INV-004`](tasks/INV-004.md) | DONE / PRESERVED | - | buddy-v2 | INV-002, REC-002, AUTH-V2-001; Backend. |
| [`INV-005`](tasks/INV-005.md) | DONE / PRESERVED | - | buddy-v2 | INV-003, BUDDY-001, PROFILE-V2-001, CHAT-001 when conversation creation is included; Backend + Database. |
| [`INV-006`](tasks/INV-006.md) | DONE / PRESERVED | - | buddy-v2 | INV-003/005; Backend + Database. |
| [`INV-007`](tasks/INV-007.md) | DONE / PRESERVED | - | buddy-v2 | INV-004..006, REC-004; Frontend. |
| [`INV-008`](tasks/INV-008.md) | DONE / PRESERVED | - | buddy-v2 | INV-003, MAIL-001; Backend + Infrastructure. |
| [`INV-009`](tasks/INV-009.md) | DONE / PRESERVED | - | buddy-v2 | INV-005, MAIL-001; Backend + Frontend + Infrastructure. |
| [`MAIL-001`](tasks/MAIL-001.md) | DONE / PRESERVED | - | auth-email | BE-004, EMAIL-001; Backend + Database + Infrastructure. |
| [`MATCH-001`](tasks/MATCH-001.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | buddy-v2 | BE-010 |
| [`MATCH-002`](tasks/MATCH-002.md) | RECONTRACT REQUIRED | P1 | buddy-v2 | MATCH-001 |
| [`MATCH-003`](tasks/MATCH-003.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | buddy-v2 | MATCH-007, BE-009 |
| [`MATCH-004`](tasks/MATCH-004.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | buddy-v2 | MATCH-003, MATCH-007 |
| [`MATCH-005`](tasks/MATCH-005.md) | PLANNED / BACKLOG | P2 | buddy-v2 | MATCH-003, MATCH-007 |
| [`MATCH-006`](tasks/MATCH-006.md) | PLANNED / BACKLOG | P2 | buddy-v2 | MATCH-003, MATCH-007 |
| [`MATCH-007`](tasks/MATCH-007.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | buddy-v2 | MATCH-001, BE-016 |
| [`MATCH-008`](tasks/MATCH-008.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | buddy-v2 | MATCH-004, AUTH-018, EVT-008 |
| [`MATCH-009`](tasks/MATCH-009.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | buddy-v2 | MATCH-014, AUTH-017 |
| [`MATCH-010`](tasks/MATCH-010.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | buddy-v2 | MATCH-009, MATCH-007, AUTH-011A |
| [`MATCH-011`](tasks/MATCH-011.md) | RECONTRACT REQUIRED | P1 | buddy-v2 | MATCH-002, AUTH-017 |
| [`MATCH-012`](tasks/MATCH-012.md) | RECONTRACT REQUIRED | P1 | buddy-v2 | MATCH-003 |
| [`MATCH-013`](tasks/MATCH-013.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | buddy-v2 | MATCH-008 |
| [`MATCH-014`](tasks/MATCH-014.md) | SUPERSEDED / DO NOT IMPLEMENT | P0 | buddy-v2 | MATCH-013, MATCH-007 |
| [`OPS-001`](tasks/OPS-001.md) | DONE / PRESERVED | - | release-operations | MAIL-001; Infrastructure + Backend. |
| [`OPS-002`](tasks/OPS-002.md) | DONE / PRESERVED | - | release-operations | EMAIL-003, OPS-001; Infrastructure + Operations. Downstream, OPS-003 depends directly on OPS-002; SEM-002 depends on OPS-003 and therefore SEM-004..007 and ACCEPT-001 depend ind... |
| [`OPS-003`](tasks/OPS-003.md) | DONE / PRESERVED | - | release-operations | OPS-002; Infrastructure + Operations. |
| [`PREF-001`](tasks/PREF-001.md) | DONE / PRESERVED | - | buddy-v2 | BE-009/010; Database + Backend. |
| [`PREF-002`](tasks/PREF-002.md) | DONE / PRESERVED | - | buddy-v2 | PREF-001; Backend. |
| [`PREF-003`](tasks/PREF-003.md) | DONE / PRESERVED | - | buddy-v2 | PREF-001/002, BE-012/015; Backend. |
| [`PREF-004`](tasks/PREF-004.md) | DONE / PRESERVED | - | buddy-v2 | PREF-003, FE-026/027/029; Frontend. |
| [`PROD-001`](tasks/PROD-001.md) | BLOCKED / OWNER ACTION REQUIRED | release | release-operations | Private Semester backup failed; no retained Render rollback point, named owners or accepted post-repair hold. |
| [`PROFILE-V2-001`](tasks/PROFILE-V2-001.md) | DONE / PRESERVED | - | buddy-v2 | BUDDY-001, BE-012; Backend + Database. |
| [`PROFILE-V2-002`](tasks/PROFILE-V2-002.md) | DONE / PRESERVED | - | buddy-v2 | PROFILE-V2-001, FE-029; Frontend. |
| [`REC-001`](tasks/REC-001.md) | DONE / PRESERVED | - | buddy-v2 | AUTH-V2-001, PREF-003; Backend. |
| [`REC-002`](tasks/REC-002.md) | DONE / PRESERVED | - | buddy-v2 | REC-001; Backend. |
| [`REC-003`](tasks/REC-003.md) | DONE / PRESERVED | - | buddy-v2 | REC-002, AUTH-V2-001; Backend. |
| [`REC-004`](tasks/REC-004.md) | DONE / PRESERVED | - | buddy-v2 | REC-003, EMAIL-005; Frontend. |
| [`SEM-001`](tasks/SEM-001.md) | DONE / PRESERVED | - | semester | BUDDY-001, CHAT-001, existing User/Audit; Database + Backend. |
| [`SEM-002`](tasks/SEM-002.md) | DONE / PRESERVED | - | semester | SEM-001, OPS-003; Backend + Database + Infrastructure. |
| [`SEM-003`](tasks/SEM-003.md) | DONE / PRESERVED | - | semester | SEM-001, EVS-003; Backend + Storage Infrastructure. |
| [`SEM-004`](tasks/SEM-004.md) | DONE / PRESERVED | - | semester | SEM-002/003, OPS-001; Backend + Infrastructure. |
| [`SEM-005`](tasks/SEM-005.md) | DONE / PRESERVED | - | semester | SEM-004, AUTH-018, EVT-008; Backend + Database + Storage + Operations. |
| [`SEM-006`](tasks/SEM-006.md) | DONE / PRESERVED | - | semester | SEM-005; Backend + Database + Storage + Operations. |
| [`SEM-007`](tasks/SEM-007.md) | DONE / PRESERVED | - | semester | SEM-005/006, ADMIN-005; Frontend. |
