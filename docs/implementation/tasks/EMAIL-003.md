# EMAIL-003

**Control-plane status:** DONE / PRESERVED
**Track:** auth-email
**Priority:** -
**Dependencies (latest extracted):** EMAIL-001A; Backend + Database.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 6944-6954

#### EMAIL-003 — Confirm verification token

- **Status:** **Done 2026-09-24.** The authenticated USER endpoint atomically consumes a valid current-address token and stamps `email_verified_at`; failures stay generic and the response exposes only a fixed internal redirect target.
- **Purpose:** Atomically verify only the token's current user/email snapshot.
- **Scope / likely files:** auth endpoint/service/schema and frontend-safe redirect result contract.
- **Dependencies / ownership:** EMAIL-001A; Backend + Database.
- **Security:** constant-safe digest lookup/compare, one transaction, no open redirect, generic invalid/expired response.
- **Acceptance / DoD:** one valid unexpired unused token sets `email_verified_at`, consumes/supersedes tokens and succeeds once; changed email, replay and race fail safely.
- **Tests/gates:** exact 15-minute boundary, replay, simultaneous confirmations, changed-email and deleted/inactive account tests.
- **Non-goals:** login or automatic invitation action.


## Cross-reference occurrences outside extracted headings

- Legacy line 6852: | EMAIL-003 (**Done 2026-09-24**) | Confirm verification | EMAIL-001A | One valid token atomically stamps current email | Expiry/replay/race tests |
- Legacy line 6893: | OPS-002 | Early staging infrastructure validation + free-tier email-worker acceptance | EMAIL-003, OPS-001 | Existing staging topology plus Supabase Cron -> Edge Function -> Resend with atomic claim, bounded batch, retry, idempotency, overlap safety and Free-plan validation | Restore rehearsal + deployed Edge-worker acceptance record |
- Legacy line 8102: - **Dependencies / ownership:** EMAIL-003, OPS-001; Infrastructure + Operations. Downstream, OPS-003 depends directly on OPS-002; SEM-002 depends on OPS-003 and therefore SEM-004..007 and ACCEPT-001 depend indirectly on this gate. Invitation/accepted email tasks retain their MAIL-001 dependencies and their functional requirements; this deployment decision does not remove or weaken them.
- Legacy line 8159: EMAIL-001A → EMAIL-003
- Legacy line 8161: (EMAIL-002 + EMAIL-003 + EMAIL-004) → EMAIL-005
- Legacy line 8194: (EMAIL-003 + OPS-001) → OPS-002 → OPS-003
- Legacy line 8242: The **first reasonable staging deployment is OPS-002**, immediately after **EMAIL-003 + OPS-001** and existing Auth/Profile/avatar foundations pass locally. This is an early infrastructure-validation deployment, not a product release. Its purpose is to validate Vercel→FastAPI same-site cookie/CSRF topology, HTTPS, migrations, TLS Redis, private Supabase Storage, Cron/Edge/outbox email delivery, deep links and WSS-capable hosting before building the remaining vertical slice.
