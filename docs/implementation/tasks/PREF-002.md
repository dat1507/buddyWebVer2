# PREF-002

**Control-plane status:** DONE / PRESERVED
**Track:** buddy-v2
**Priority:** -
**Dependencies (latest extracted):** PREF-001; Backend.

> Focused extract generated from the legacy plan on 2026-10-08. Apply the current status and
> precedence in `../../../implementation-plan.md`; older excerpts are preserved history, not
> automatic authorization. Source: `../../../implementation_plan_vgu_buddy.md`.

## Preserved contract sections

### Legacy lines 7015-7039

#### PREF-002 — Normalized preference identity service

- **Status:** **Done 2026-09-27.** The backend now owns one bounded, deterministic preference identity contract with a display-safe label and an NFKC/whitespace/casefold key; PREF-003/PREF-004 remain unimplemented.
- **Purpose:** Define the single deterministic identity rule shared by persistence, duplicate detection and scoring.
- **Scope / likely files:** pure normalization/value-object service implementing NFKC → trim → collapse whitespace → Unicode casefold, with display-label validation.
- **Dependencies / ownership:** PREF-001; Backend.
- **Security:** bound input before/after normalization; reject empty/control-character output; never use locale-dependent comparison.
- **Acceptance / DoD:** `Photography` equals `photography`; compatibility-equivalent Unicode/whitespace forms share a key; `Football` differs from `Soccer`; output is deterministic across supported runtime.
- **Tests/gates:** Unicode normalization vectors, whitespace/case/property/idempotency and pathological input tests.
- **Non-goals:** persistence, semantic translation, fuzzy matching or AI.

**Implementation:** `PreferenceIdentity` is an immutable value object that returns the cleaned
display label separately from the deterministic comparison key. Display labels preserve valid
Unicode and casing while trimming/collapsing whitespace; keys apply NFKC, trim/collapse whitespace
and Unicode casefold in that order. The service reuses the PREF-001 120/255-character storage
bounds, rejects oversized input before normalization and rejects empty, unsafe control/format and
post-normalization oversized values. It has no database, locale, timezone or external-service
dependency.

**Verification (2026-09-27):** Golden Unicode/casefold/NFKC/whitespace, immutability, idempotency,
pathological-input and PREF-001 identity-compatibility tests pass. Full backend: 836 passed / 20
configured live skips; Ruff, strict mypy (156 files), dependency consistency/audit, Alembic
history/head, package build and Compose validation pass. No migration, persistence, API or frontend
change was added.


## Cross-reference occurrences outside extracted headings

- Legacy line 6857: | PREF-002 | Normalized preference identity service | PREF-001 | NFKC/casefold rules and deterministic keys | Unicode/property tests |
- Legacy line 7044: - **Scope / likely files:** profile schemas/services/routes and readiness calculation using PREF-002 keys.
- Legacy line 7056: Custom labels use the PREF-002 identity service and are rejected with a stable sanitized 422 when
- Legacy line 7085: PREF-002 contract, enforce combined per-kind limits, explain same-kind normalized duplicates and
- Legacy line 8163: PREF-001 → PREF-002 → PREF-003 → PREF-004
