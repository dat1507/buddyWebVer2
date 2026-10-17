# Incidents and troubleshooting history

These are engineering troubleshooting cases supported by retained evidence. They are not
all Production outages, and duration/impact is not invented where absent.

## WebSocket regression gate: test-harness race (Oct 9–10)

**Symptoms:** full backend regression reported two WebSocket fanout/unread failures during
Event integration. **Investigation:** the initial local run used Python 3.14 while CI/Docker
targeted 3.12; reproduction identified fake Redis queue publication on a different event loop
and cancellation racing asynchronous subscription teardown. **Resolution:** publish through
the TestClient portal, close sockets explicitly and wait for deterministic fake cleanup.
Application WebSocket behavior was unchanged. **Verification:** supported-runtime full and
focused suites passed; final acceptance increased to 1,408 PASS / 37 SKIP. **Lesson:** distinguish
test transport lifetime from application defects before changing runtime code.

Evidence: [EVS-007](../../implementation/tasks/EVS-007.md), `81d42c3`/`e2ef4c0`,
[local acceptance](../../operations/accept-event-001-local-acceptance-2026-10-10.md).
The runtime difference was context; the recorded race is the identified cause.

## Semester restore permissions and staged copies (Oct 4–7)

**Symptoms/problem:** restore execution required privileges and safe ordering beyond ordinary
runtime writes; later cohort activity had to prevent recovery from overwriting new data.
**Investigation/evidence:** `9ae721d`, `ba3a139`, `47cf078`, `5100d8b`, `3f14150` and
reconciliation records show narrow restore permissions, staged-copy-before-insert handling,
semester isolation and guarded restore-block finalization. **Resolution:** scoped functions/
permissions, safe restore sequencing and monotonic new-USER blocking. **Verification:** dated
staging reset/restore and restore-block-after-new-USER acceptance. **Lesson:** a restore is a
transactional domain operation with irreversible cohort boundaries, not a blind import.

Exact original SQL errors and every investigation step are not reconstructed from commit
subjects alone. Source: [reconciliation](../../operations/accept-001-reconciliation-2026-10-04.md),
[SEM-006](../../implementation/tasks/SEM-006.md),
[Production status](../../implementation/production-status.md). Production backup failure below
is a distinct unresolved boundary.

## Production private Semester backup failure (observed Oct 8, open)

**Symptoms:** Prepare returned retained 503 responses; operation recorded
`RESET_PREPARATION_FAILED`, private backup `FAILED` and unverified. **Investigation:** direct
operator evidence established failure; the audit does not establish a repaired root cause.
**Resolution:** none claimed. **Verification:** no retry or mutation was performed for this audit.
**Prevention/next investigation:** separately authorize private-backup access diagnosis and safe
acceptance, then supply recovery owners and accepted post-repair hold. Do not mark readiness
or successful unrelated tests as recovery evidence.

Evidence: [PROD technical record](../../operations/prod-001-technical-evidence-2026-10-08.md),
[PROD-001](../../implementation/tasks/PROD-001.md).

## Landing slideshow blank/unstable transitions (Oct 9)

**Symptoms:** the first campus slideshow needed corrective transition behavior. **Resolution:**
decode-aware stable image-layer transitions in `c2fbaf1`; avoid replacing a source while its
layer is visible. **Verification:** recorded 15 transitions/three loops, desktop/mobile,
reload/reduced-motion, no blank/undecoded/source-swap/overflow samples; owner accepted smoothness.
**Lesson:** image readiness and opacity timing are separate requirements.

Evidence: [FE-LANDING-BG-002](../../implementation/tasks/FE-LANDING-BG-002.md).
No new visual/performance measurement was made here.

## Public Event content-consistency rollback (Oct 14)

**Symptoms:** Slider/detail routing and rendering passed, but the Kawazo poster's advertised
date/time disagreed with canonical detail. **Cause:** content inconsistency, not a proven
routing or database corruption bug. **Resolution:** rollout stopped, retained Admin-ON/public-OFF
Vercel artifact promoted; future-build public flag disabled. The owner later accepted the
poster discrepancy as out of scope, and the exact frontend release was activated again.
**Verification:** dated recovery and final public/Admin smoke. **Lesson:** content truth can
be a release gate even when technical checks pass; owner acceptance changes scope, not history.

Evidence: [preflight/release record](../../operations/event-kawazo-production-release-preflight-2026-10-14.md),
[task](../../implementation/tasks/FE-EVENT-DETAIL-TEMPLATE-001.md). Do not describe this as a
poster correction: no such correction was required by the final decision.

## Event local acceptance regressions (Oct 10)

Recorded acceptance found async `updated_at` projection, detail session bootstrap, empty-state
and phase-boundary issues. `e2ef4c0` and focused tests close the isolated acceptance boundary.
These are local acceptance discoveries, not documented Production incidents. Consult
[the evidence](../../operations/accept-event-001-local-acceptance-2026-10-10.md) for exact cases;
do not extrapolate an outage, duration or affected users.

## Incident entry standard

For a future incident, capture dated symptom/environment, observed impact, reproducer,
root-cause confidence, source diff, verification and remaining risk. Mark hypotheses separately.
Never paste live payloads, account identities, signed URLs, secrets or raw provider logs.
