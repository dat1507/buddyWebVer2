# PROD-001

**Control-plane status:** IN PROGRESS / READY
**Track:** release-operations
**Priority:** release
**Dependencies (latest extracted):** ACCEPT-001 and explicit release approval; Operations + Engineering.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 8138-8147

#### PROD-001 — Production release, smoke and rollback hold point

- **Purpose:** Release only after every functional, security, infrastructure and operational gate is satisfied.
- **Scope / likely files:** release checklist/change record; apply migrations with backup, deploy the Cron/Edge email transport plus backend/frontend, smoke, observe and retain rollback point. No always-on hosted Python email worker is part of PROD-001.
- **Dependencies / ownership:** ACCEPT-001 and explicit release approval; Operations + Engineering.
- **Security:** final secret/history scan, credential rotation status, secure cookie/CORS/CSRF/proxy/TLS verification, private backup access and destructive-control review.
- **Acceptance / DoD:** production smoke covers auth/profile/verification/recommendations/invitation/Current Buddies/chat/Admin read paths without destructive reset; monitoring stable through hold period; rollback/recovery owners are available. Semester Reset is not run in production merely to prove deployment.
- **Tests/gates:** signed release approval, migration backup/check, health/WSS/email smoke, error-rate observation and rollback readiness.
- **Non-goals:** using production as the first reset/restore test environment.


## Cross-reference occurrences outside extracted headings

- Legacy line 6896: | PROD-001 | Production release and verification | ACCEPT-001 | All release gates met; rollback point captured | Production smoke/monitoring gate |
- Legacy line 8197:   → ACCEPT-001 → PROD-001
- Legacy line 8211: 7. Converge all functional branches at \`ACCEPT-001\`; only then run \`PROD-001\` after explicit release approval.
- Legacy line 8260: **Production is NOT READY.** The final production gate is **ACCEPT-001 completed on production-like staging, followed by explicit PROD-001 approval**. Unit tests alone can never satisfy this gate.
- Legacy line 8295: | **PRODUCTION** | **NOT READY** | Requires all functional/security/infrastructure/operational gates, destructive staging rehearsal and ACCEPT-001; PROD-001 is the final release gate. |
- Legacy line 8299: ACCEPT-001 for production-like staging acceptance; PROD-001 remains gated on that signed result and
- Legacy line 9173:   with newly generated isolated values during \`PROD-001\`.
