# SEC-DEV-MINIMATCH-001 — Compatible lint-toolchain security follow-up

Status READY — FOLLOW-UP / NOT ASSIGNED. Owner requested separate follow-up2026-10-31.
GHSA-g3hv-75wg-m249 remains reported for minimatch3.1.5/10.2.6 and13 parent tooling entries.
Affected path is pattern amplification at optimizationLevel>=2; installed3 lacks that method,
installed10 defaults to1, and typescript-estree calls with dot:true only. Repository ESLint config
uses fixed trusted globs and does not enable project-service/optimizationLevel2. No runtime usage.
Scoped release exception: development/CI availability risk accepted for this unchanged UI candidate;
no audit suppression or forced incompatible11 override. Full npm audit remains nonzero and visible.
Revisit by2026-11-30, or before accepting untrusted glob patterns, enabling optimizationLevel2,
changing lint configuration or promoting this dependency to runtime, whichever is earlier.
Assess upstream backports and compatible ESLint/typescript-eslint changes; preserve glob semantics,
run lint/types/affected tests/build/audits. Include the existing ESLint9 support deprecation in that
maintenance review. Do not broadly upgrade tooling or implement without a separate assignment.
