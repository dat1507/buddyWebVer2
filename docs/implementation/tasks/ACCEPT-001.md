# ACCEPT-001

**Control-plane status:** OPEN / POST-DEPLOY HARDENING
**Track:** release-operations
**Priority:** -
**Dependencies (latest extracted):** EMAIL/PREF/PROFILE/REC/INV/BUDDY/CHAT/ADMIN V2 tasks, SEM-007, CHAT-005, OPS-003; QA + Product + Engineering + Operations.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 8128-8137

#### ACCEPT-001 — Full Buddy Matching V2 staging acceptance

- **Purpose:** Prove the complete product and recovery story on production-like infrastructure.
- **Scope / likely files:** E2E fixtures/scripts and signed acceptance checklist; no new business behavior.
- **Dependencies / ownership:** EMAIL/PREF/PROFILE/REC/INV/BUDDY/CHAT/ADMIN V2 tasks, SEM-007, CHAT-005, OPS-003; QA + Product + Engineering + Operations.
- **Security:** dedicated test users/data; destructive scenarios only in isolated staging; secrets/redaction review and diff inspection.
- **Acceptance / DoD:** production-like migration proves legacy USER rows are UNVERIFIED without authoritative timestamp evidence while ADMIN bootstrap/login remains usable. Real Vietnamese and International accounts verify real emails; recommendation/invitation email/Accept/accepted email/multiple Buddies/chat/read/retention/F5/logout/login work. Invitation composer/API agree on trimming, non-whitespace-run word counts and 500/501 plus 10,000/10,001-code-point boundaries, with inert plain-text rendering. After Accept, backend and stale-tab UI both reject a type change, the profile field is locked/explained, and existing Matches remain unchanged. Email change locks and reverify unlocks; Admin monitoring reconciles; reset backs up DB+avatars, deletes USER data, restores, then a second rehearsal proves restore blocked after a new USER. A completed reset/new cohort proves the deleted old account does not carry its type lock and a newly registered account can choose its type normally.
- **Tests/gates:** all automated suites, migration/live Redis/Storage/email/WSS tests, browser E2E, accessibility smoke, shared message-validation fixtures, Accept-vs-type-update load/race tests and recorded manual evidence pass.
- **Non-goals:** production deployment or synthetic-only acceptance.


## Cross-reference occurrences outside extracted headings

- Legacy line 13: > \`RESTORE_BLOCKED_NEW_DATA\`. Full signed \`ACCEPT-001\` and the complete encrypted off-site DR
- Legacy line 39: > **Runtime acceptance update — 2026-09-23 (historical v2.2 acceptance):** The local environment was configured, the development database was at \`0007_event_tables (head)\`, Supabase Storage configuration was idempotent, and a real authenticated Profile/avatar upload-crop-refresh-F5 persistence path passed. The old “two-user plus Admin matching run” gate is superseded by ACCEPT-001.
- Legacy line 6720: | Backend/DB deployment | **Staging foundation accepted; production pending** | FastAPI staging, separated runtime/migration roles, migration \`0010\`, DB/Redis/email/storage readiness, WSS upgrade and trusted proxy gates are recorded in OPS-002 evidence | Keep the accepted staging topology. OPS-003 supplies rollback/recovery; production still requires the later V2 and ACCEPT-001 gates. |
- Legacy line 6895: | ACCEPT-001 | Full V2 staging acceptance | All functional tasks, SEM-007, OPS-003 | Real two-user happy path + reset/restore/block scenarios | Signed acceptance record |
- Legacy line 6896: | PROD-001 | Production release and verification | ACCEPT-001 | All release gates met; rollback point captured | Production smoke/monitoring gate |
- Legacy line 8102: - **Dependencies / ownership:** EMAIL-003, OPS-001; Infrastructure + Operations. Downstream, OPS-003 depends directly on OPS-002; SEM-002 depends on OPS-003 and therefore SEM-004..007 and ACCEPT-001 depend indirectly on this gate. Invitation/accepted email tasks retain their MAIL-001 dependencies and their functional requirements; this deployment decision does not remove or weaken them.
- Legacy line 8142: - **Dependencies / ownership:** ACCEPT-001 and explicit release approval; Operations + Engineering.
- Legacy line 8197:   → ACCEPT-001 → PROD-001
- Legacy line 8211: 7. Converge all functional branches at \`ACCEPT-001\`; only then run \`PROD-001\` after explicit release approval.
- Legacy line 8224: Final integration convergence: EMAIL-005 + PREF-004 + PROFILE-V2-002 + REC-004 + INV-007/008/009 + BUDDY-003 + CHAT-004/005 + ADMIN-V2-002 + SEM-007 + OPS-003 must all pass before ACCEPT-001.
- Legacy line 8244: The **second mandatory staging milestone** is after the complete user vertical slice **through PROFILE-V2-002 and CHAT-004 plus INV-008/009 and ADMIN-V2-002**. It validates two real verified users from recommendation through invitation/email/Accept/Current Buddies/chat, including exact invitation boundaries and the post-Accept type lock. Staging remains incomplete until **SEM-007 + CHAT-005 + OPS-003** and ACCEPT-001 prove reset/backup/restore/blocking and retention.
- Legacy line 8260: **Production is NOT READY.** The final production gate is **ACCEPT-001 completed on production-like staging, followed by explicit PROD-001 approval**. Unit tests alone can never satisfy this gate.
- Legacy line 8294: | **STAGING** | **OPS-002 AND OPS-003 DONE** | Early infrastructure, restore/migration, Edge/Cron A–F, real verification acceptance and primary/backup alert routing passed. The implemented PROFILE-V2-002 + CHAT-004 + INV-008/009 + ADMIN-V2-002 vertical slice still needs staging acceptance; release-candidate staging requires SEM-007 and ACCEPT-001. |
- Legacy line 8295: | **PRODUCTION** | **NOT READY** | Requires all functional/security/infrastructure/operational gates, destructive staging rehearsal and ACCEPT-001; PROD-001 is the final release gate. |
- Legacy line 8297: **Next step: \`ACCEPT-001 — Full V2 staging acceptance\`.** SEM-007 now completes the Admin safety UX
- Legacy line 8299: ACCEPT-001 for production-like staging acceptance; PROD-001 remains gated on that signed result and
- Legacy line 9084: - **Next Task:** complete remaining Admin/core staging acceptance, then \`ACCEPT-001\`.
- Legacy line 9090: 3. \`ACCEPT-001\` — run full Buddy Matching V2 staging/regression acceptance.
- Legacy line 9120: - **Scope boundary / next task:** \`ADMIN-013\` remains **NOT STARTED**. \`ACCEPT-001\` remains blocked and
- Legacy line 9147: - **Scope boundary / next task:** \`ACCEPT-001\` remains **BLOCKED** and was not resumed. The next
- Legacy line 9174: - **\`ACCEPT-001\`:** remains **OPEN / BLOCKING**. Reuse accepted evidence and run only the missing
- Legacy line 9180: - **Production readiness:** **NOT READY / BLOCKED** by remaining \`ACCEPT-001\`, DR evidence and
