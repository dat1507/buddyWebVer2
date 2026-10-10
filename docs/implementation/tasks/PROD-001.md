# PROD-001

**Control-plane status:** BLOCKED / OWNER ACTION REQUIRED
**Track:** release-operations
**Priority:** release
**Dependencies (latest extracted):** ACCEPT-001 and explicit release approval; Operations + Engineering.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Later rollback update — 2026-10-10

The controlled Event code rollout created a second successful Render deploy. Live application SHA
`e2ef4c0` now has a native provider rollback action to retained `d15cb1d`; Vercel also retains READY
frontend candidates. This closes the missing-backend-code-rollback blocker recorded below. It does
not close `PROD-001`: the failed/unverified private Semester backup, named rollback/recovery owners
and accepted post-repair hold duration remain unresolved. See
[`accept-event-001-production-release-2026-10-10.md`](../../operations/accept-event-001-production-release-2026-10-10.md).

## Technical evidence closure update — 2026-10-08 15:01 Asia/Saigon

- Secure host-only cookie metadata, session reload/logout, CSRF coverage, authenticated WSS
  Origin/auth/reconnect, REST history recovery and non-destructive Semester guard/status are PASS.
- The focused verification passed 60 web tests and 143 API tests. The final high-confidence
  tracked-content/Git-history secret scan found no live-secret pattern; credential-URL matches were
  localhost fixtures/examples only.
- Vercel retains the current and prior Ready frontend deployments. Render reports only one backend
  deploy, so no previous backend revision is selectable as a rollback point.
- Production Semester status is a real blocker: the latest reset preparation is `FAILED` with
  `RESET_PREPARATION_FAILED`; its private backup is `FAILED` and unverified. Provider logs retain two
  earlier Prepare responses of 503. No Prepare/Execute/Reset/Restore action was run during this
  verification.
- No rollback/recovery owner names or accepted post-repair hold duration were supplied.

Decision: `PROD-001` remains open and is now **BLOCKED / OWNER ACTION REQUIRED**. It may become DONE
only after private-backup access is repaired and safely evidenced under separate authorization, a
backend rollback/redeploy point exists, named owners are recorded and the agreed post-repair hold
passes. See
[`prod-001-technical-evidence-2026-10-08.md`](../../operations/prod-001-technical-evidence-2026-10-08.md).

## Earlier acceptance update — 2026-10-08

- First-party DNS, public live/readiness, frontend API target, anonymous auth boundary and
  exact-origin CORS are PASS.
- The owner explicitly confirmed PASS with no functional errors for Admin login/Dashboard, User
  login/Dashboard, Buddy Recommendation, Invitations, Accept Invitation, Buddy Matching, Chat and
  related features. Do not rerun these paths solely to collect another record.
- Still open: Secure host-only cookie/session/CSRF evidence; protocol-level authenticated WSS
  Origin/auth/reconnect and REST recovery; non-destructive Semester and final release-security
  review; hold-period telemetry, retained rollback points and named recovery owners.

Decision: `PROD-001` cannot be marked DONE yet because the preserved Definition of Done requires
the remaining security, observation and rollback evidence. Continue the same Task ID; no feature or
source implementation is required.

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
