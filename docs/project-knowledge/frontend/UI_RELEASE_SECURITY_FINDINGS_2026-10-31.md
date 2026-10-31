# UI release dependency findings — 2026-10-31

Original frontend report:20 package entries but19 unique advisory IDs.18 unique findings remediated;
the one remaining advisory propagates to14 moderate package entries. No high/critical findings remain.
Original backend report:17 rows but16 unique IDs (certifi was duplicated); all16 remediated.
Fresh npm runtime audit0; Python explicit runtime lock37 rows/0 and full dev lock81 rows/0, no skipped
rows. Compared with prior resolved36/79, explicit audits additionally cover packaging and wheel.
Raw data, exact versions and dependency graph changes: primary `.local/ui-release-blockers/`.

## Exposure and compatible remediation

All affected npm nodes are dev-only. Vite/launch-editor and Vitest expose developer-server surfaces;
undici enters through jsdom tests, and source-map-js/PostCSS process build inputs. Vercel serves the
generated static app; none of these tools is its application server. Patch releases address these
before publication. Exact Vite8.2.4/Vitest5.0.3 pins and three compatible transitive overrides avoid
unrelated dependency refreshes. Vitest's required companion changes (including magic-string and
why-is-node-running) and removal of obsolete stackback/siginfo are retained, not forced overrides.

Python findings enter the development audit/build stack through cachecontrol/pip-audit/pip-tools:
msgpack parsing, certifi CA trust, filelock local cache paths, setuptools legacy Windows wheel install.
No API application import uses these packages; runtime requirements/Dockerfile/pyproject are unchanged.
Only four dev-lock pins change. Filelock4.2.1 is the deliberate transitive major required by the
published fixes, allowed by cachecontrol's dependency range; pip check, actual audits and all backend
gates verify compatibility. No new application API, backend deployment or migration is required.

## Unique npm advisories

| Package / installed before    | Advisory                                                                 | Published affected range | Candidate disposition                                              |
| ----------------------------- | ------------------------------------------------------------------------ | ------------------------ | ------------------------------------------------------------------ |
| @vitest/mocker 5.0.0          | [GHSA-qxg6-89mg-rqv8](https://github.com/advisories/GHSA-qxg6-89mg-rqv8) | `>=5.0.0-beta.1 <5.0.3`  | 5.0.3 via Vitest5.0.3                                              |
| @vitest/mocker 5.0.0          | [GHSA-xp26-3454-mjgp](https://github.com/advisories/GHSA-xp26-3454-mjgp) | `>=5.0.0-rc.2 <5.0.3`    | 5.0.3 via Vitest5.0.3                                              |
| minimatch 3.1.5 /10.2.6       | [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) | `<11.0.1`                | Scoped exception; only published patch11.0.1 is a major/API change |
| postcss-selector-parser 6.1.4 | [GHSA-rj75-hqrm-r3gf](https://github.com/advisories/GHSA-rj75-hqrm-r3gf) | `<6.1.5`                 | 6.1.5                                                              |
| source-map-js 1.2.1           | [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) | `>=1.0.0 <1.2.2`         | 1.2.2                                                              |
| undici 7.29.1                 | [GHSA-4qv8-2p9j-2685](https://github.com/advisories/GHSA-4qv8-2p9j-2685) | `>=7.0.0 <7.30.1`        | 7.30.1                                                             |
| undici 7.29.1                 | [GHSA-f72v-6w45-q472](https://github.com/advisories/GHSA-f72v-6w45-q472) | `>=7.15.0 <7.30.1`       | 7.30.1                                                             |
| undici 7.29.1                 | [GHSA-xjj6-f33q-929c](https://github.com/advisories/GHSA-xjj6-f33q-929c) | `>=7.18.0 <7.30.1`       | 7.30.1                                                             |
| undici 7.29.1                 | [GHSA-4w7w-5xrc-9h26](https://github.com/advisories/GHSA-4w7w-5xrc-9h26) | `>=7.0.0 <7.30.1`        | 7.30.1                                                             |
| undici 7.29.1                 | [GHSA-2m5v-pch6-74hx](https://github.com/advisories/GHSA-2m5v-pch6-74hx) | `>=7.0.0 <7.30.1`        | 7.30.1                                                             |
| undici 7.29.1                 | [GHSA-qrxm-fqhp-jwvm](https://github.com/advisories/GHSA-qrxm-fqhp-jwvm) | `>=7.0.0 <7.30.1`        | 7.30.1                                                             |
| undici 7.29.1                 | [GHSA-9fm3-97px-rjf6](https://github.com/advisories/GHSA-9fm3-97px-rjf6) | `>=7.0.0 <7.30.1`        | 7.30.1                                                             |
| undici 7.29.1                 | [GHSA-55wc-3pg8-jfw6](https://github.com/advisories/GHSA-55wc-3pg8-jfw6) | `>=7.15.0 <7.30.1`       | 7.30.1                                                             |
| vite 8.2.2                    | [GHSA-698v-4r3x-3vcv](https://github.com/advisories/GHSA-698v-4r3x-3vcv) | `>=8.2.0 <=8.2.3`        | 8.2.4                                                              |
| vite 8.2.2                    | [GHSA-r825-w8mm-5pxw](https://github.com/advisories/GHSA-r825-w8mm-5pxw) | `>=8.2.0 <=8.2.3`        | 8.2.4                                                              |
| vite 8.2.2                    | [GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm) | `>=8.2.0 <=8.2.3`        | 8.2.4                                                              |
| vite 8.2.2                    | [GHSA-9jrq-w75r-8gcw](https://github.com/advisories/GHSA-9jrq-w75r-8gcw) | `>=8.2.0 <=8.2.3`        | 8.2.4                                                              |
| vite 8.2.2                    | [GHSA-rq7h-c2jc-7f22](https://github.com/advisories/GHSA-rq7h-c2jc-7f22) | `>=8.2.0 <=8.2.3`        | 8.2.4                                                              |
| vite 8.2.2                    | [GHSA-vfpm-58rq-9qcg](https://github.com/advisories/GHSA-vfpm-58rq-9qcg) | `>=8.2.0 <=8.2.3`        | 8.2.4                                                              |

## Unique Python advisories

| Package / installed before | Advisory                                                                 | Fixed selected version |
| -------------------------- | ------------------------------------------------------------------------ | ---------------------- |
| msgpack 1.2.2              | [GHSA-j586-36cw-2gc2](https://github.com/advisories/GHSA-j586-36cw-2gc2) | 1.2.3                  |
| certifi 2026.7.22          | [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) | 2026.10.18             |
| filelock 3.32.7            | [GHSA-v4x8-3wr5-3wq8](https://github.com/advisories/GHSA-v4x8-3wr5-3wq8) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-9vhv-jxww-xfm5](https://github.com/advisories/GHSA-9vhv-jxww-xfm5) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-567q-5qvw-pf92](https://github.com/advisories/GHSA-567q-5qvw-pf92) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-m462-7rxw-wvpg](https://github.com/advisories/GHSA-m462-7rxw-wvpg) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-j8f7-rjxc-mr56](https://github.com/advisories/GHSA-j8f7-rjxc-mr56) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-8mx5-7m5m-r77g](https://github.com/advisories/GHSA-8mx5-7m5m-r77g) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-69hj-f68j-2879](https://github.com/advisories/GHSA-69hj-f68j-2879) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-9c4x-gm8v-wgc4](https://github.com/advisories/GHSA-9c4x-gm8v-wgc4) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-rfpc-qcw5-3pc4](https://github.com/advisories/GHSA-rfpc-qcw5-3pc4) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-cwqr-hh33-gh44](https://github.com/advisories/GHSA-cwqr-hh33-gh44) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-fq56-3cx3-fjxp](https://github.com/advisories/GHSA-fq56-3cx3-fjxp) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-9j6q-wvj5-jgjg](https://github.com/advisories/GHSA-9j6q-wvj5-jgjg) | 4.2.1                  |
| filelock 3.32.7            | [GHSA-6627-m3xw-93mp](https://github.com/advisories/GHSA-6627-m3xw-93mp) | 4.2.1                  |
| setuptools 84.0.0          | [GHSA-xmj3-9gf7-h52w](https://github.com/advisories/GHSA-xmj3-9gf7-h52w) | 84.1.0                 |

## Remaining scoped risk — SEC-DEV-MINIMATCH-001

GHSA-g3hv-75wg-m249 is a development/CI CPU-exhaustion risk under attacker-selected patterns and
optimizationLevel>=2. Inspected minimatch3.1.5 lacks firstPhasePreProcess; minimatch10.2.6 defaults
to1. Its typescript-estree caller passes only dot:true, and this ESLint config uses trusted fixed
globs, without the project-service path. No backend/frontend user-input path reaches this tool.
The broad published range still produces14 moderate audit entries; they are not14 vulnerabilities.
Do not force minimatch11 into consumers requiring3/10. This release assessment accepts the limited
residual tooling availability risk under the unchanged configuration, with a follow-up deadline and
invalidation conditions. This is not an owner blanket acceptance or a zero-development-findings claim.
No ignore list, audit threshold change, production audit suppression or test exclusion was added.
