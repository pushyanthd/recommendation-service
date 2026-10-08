# Implementation progress

## First development slice

Implemented package/CLI scaffolding, fictional fixture data, global chronological splits, popularity, item cosine similarity, CPU ALS, seen-item filtering, ephemeral fold-in, ranking metrics, validation evaluation, local API and a small browser demo. The serving baseline is popularity; no automatic promotion is claimed.

Tests target leakage, metric arithmetic, low-rated seen items, cold-start fallback, filter preservation, finite scores, malformed requests and fixture HTTP behavior. The dependency lock and CI checks belong to this milestone.

### Verification on October 5, 2026

The documented `make setup` completes in a project-owned environment on arm64 macOS / Python 3.12.12. `make check` passes 48 tests, Ruff and strict mypy. The three-method CPU smoke trains on 29 fictional events and accounts for all four validation users per method with zero scoring failures; four final-period events remain reserved. The ALS backend is asserted to be `implicit.cpu.als`.

A temporary loopback Uvicorn process passes actual HTTP readiness, page and recommendation requests. The saved-profile request returns seven unseen titles, excluding all five of that profile's prior rated movies. The process stops after verification. This checks HTTP behavior rather than browser interaction, real-data recommendation quality or load capacity.

## Real-data evaluation milestone — October 6, 2026

Implemented explicit pinned MovieLens setup, ZIP allowlisting/size limits, preserved source terms, Latin-1 metadata parsing, checked joins/duplicates and immutable dataset/count/split identity. The prepared release contains 1,000,209 ratings and 6,040 users; demographics are not extracted. The original 48 tests still pass.

Added bounded typed benchmark rules, paired 2,000-resample intervals, cohort/coverage/concentration/fallback diagnostics, request-invariant checks, complete failure/target accounting, validation-only selection, a checksummed freeze and separate verified final refit/scoring. Report verification rejects missing/incompatible data, history, target, catalog, metric, cohort and completion evidence. An unchanged-treatment comparison additionally checks source/dependencies and model/configuration identity. Reports never silently rewrite a reference.

Generated JSON/Markdown/standalone HTML for development and final phases, with an aggregate exporter that verifies raw accounting before removing user records and private library paths. Added the fixture freeze/final/report-verification canary to CI; no real-data download enters the offline CI workflow.

### Verification

`make check` passes **92 tests**, Ruff and strict mypy. The fixture smoke and the complete CI fixture validation/freeze/final/verification sequence run offline. Independent boundaries include checksum failures, traversal/duplicate/symlink archives, byte overruns, encoding/joins, incomplete accounting, zero-baseline gates, conservative tie selection, lock contention, unchanged-treatment reproduction, escaped HTML, changed final labels, and code/rule/evidence tampering before final scoring.

The actual MovieLens development run accounts for all 1,103 eligible users per method with zero failures. Item similarity improves NDCG by 3.41%, below the fixed 10% validation objective; ALS is below popularity. Popularity is frozen for selection. The final run refits all methods and accounts for all 1,188 eligible users with zero failures, retaining 45 unreachable positives among 54,452 targets. Item similarity's final NDCG improvement is 11.97%, but this does not change the earlier selection. The final status is `experimental_quality_objective_failed`.

The final benchmark runs on an Apple M1 / MacBookPro17,1 with 16 GiB RAM, eight logical CPUs, macOS arm64 and Python 3.12.12. Per-method fits are 1.09–2.89 seconds, final process peak RSS is 958,218,240 bytes (914 MiB), and in-process scoring P95 is 0.88–1.01 ms. These are benchmark measurements, not HTTP load evidence. Dataset setup/download resources and whole-system/container memory are separate from the measured training process.

Source/count/split hashes are in [datasets/manifest.json](../datasets/manifest.json); verified public aggregate reports and their frozen decision are in [evals/2026-10-06](../evals/2026-10-06/README.md). The local raw run is `artifacts/benchmark-2026-10-06`; it is intentionally ignored by Git.

## Next milestone recorded October 6 (completed below)

Build trusted hash-verified immutable model bundles and connect the existing API to real-data snapshots. Then implement CLI activation with actual restart/readiness verification and restoration, rollback, request telemetry, the preference/baseline comparison screen, CPU packaging and the reference HTTP/fault protocols.

The research protocol and treatment remain frozen. Later serving/packaging changes must not tune the model on the inspected final labels or claim that the experimental result is a product-quality pass. The October 7 milestone below completes `make showcase`; the [acceptance checklist](acceptance.md) records the current v1 status.


## Serving and showcase milestone — October 7, 2026

Implemented immutable checksum-verified model snapshots, separate positive/all-seen CSR histories, safe NumPy loading, bounded dimensions/mappings/finiteness validation, frozen-report refit provenance, atomic initial selection and actual CLI-owned process activation/rollback. Corrupt/rejected candidates preserve the active pointer. Startup failure restores the prior process/version; a validated last-known-good pointer supports interrupted-selection recovery.

The API now loads a real-data snapshot at startup. The browser supports bounded title search, saved warm/sparse/zero-history samples, up to ten ephemeral likes, genres and same-profile baseline comparison, with explicit fixture/real/experimental provenance. Bounded Prometheus counters/histograms cover requests, errors, fallback, returned items, history lookup, scoring, filtering/top-k, total ranking and HTTP. Structured request logs omit user/movie IDs and histories. The benchmark numerical implementation remains frozen; serving parity tests cover every method.

Built and verified a digest-pinned Python 3.12 CPU image with a pinned OpenMP runtime, a portable fictional snapshot, non-root execution, read-only filesystem, no runtime network and no GPU requests. Fixed bundle-read permissions and the missing OpenMP library exposed by actual container checks. Added CI image verification and a dependency audit. The original numerical/runtime lock records remain unchanged; only the vulnerable development pytest version was updated, with the original lock retained and independently compared.

### Verification

`make check` passes **119 tests**, Ruff and strict mypy. Independent boundaries include all-method snapshot round-trips and ephemeral factor preservation, self-consistent but invalid CSR/mapping/score artifacts, checksum and pointer damage, forced quality/operation rejection, actual process restart/rollback, startup-failure restoration, stale-pointer recovery, documented CLI options, raw HTTP accounting and aggregate-export verification. The complete offline fixture validation/freeze/final/verification canary runs after the tooling update.

Chromium verifies the real saved-profile and ephemeral-like workflows, genre filtering, two comparison lists and no page errors. A local screenshot is retained under ignored `artifacts/browser/`.

The final actual-process showcase accounts for **5,000/5,000** measurement requests with **zero failures**, after 200 warmups at offered 20 requests/s and concurrency at most four. Achieved throughput is 20.00 requests/s, client P95 is 11.52 ms, and API-process peak RSS is 175.3 MiB. Snapshot load is 302.6 ms; startup-to-readiness wall time is 1831.8 ms. All four mandatory drills pass with actual files, pointer comparisons, version IDs, PIDs and numeric ranking checks. Reports bind to the current active bundle, real dataset, unchanged numerical treatment, final report and actual process code/dependency identity.

The [verified aggregate showcase](../evals/2026-10-07/README.md) passes the engineering acceptance flag. The research result remains `experimental_quality_objective_failed` and popularity stays selected. The dependency audit is clear; eight high image findings remain unfixed, with no fixable high/critical findings reported. These are retained in the system card and security evidence. No production deployment, public hosting, release tag or online-effect claim is made.

## Portfolio readiness review October 7 2026

Reverified the original raw final report, raw showcase and aggregate showcase against the active bundle/current package, and verified both dated public evidence manifests. The existing project checks pass 119 tests, Ruff and strict mypy with local socket/process access enabled.

Copied the prospective release files into an isolated directory without previous environments or artifacts, installed a non-editable wheel from the lock using an explicitly supplied dependency cache, and ran the complete fixture pipeline. Explicit setup reconstructed MovieLens from the pinned original ZIP. The documented real benchmark/final/bundle sequence then reproduced all three numerical treatment identities and every per-user metric exactly. Actual HTTP checks passed readiness, provenance, seen-item exclusion and selected-baseline parity; the test service stopped afterward. A fresh offline CPU image check passed against the same recorded image/source identities. [Reproduction evidence](../evals/reproduction-2026-10-07/README.md) retains the scope and input qualifications.

Added the [engineering case study and demo walkthrough](engineering-case-study.md), [v1 acceptance mapping](acceptance.md), current status links and the local portfolio entry. Reconciled stale serving-status prose while preserving frozen reports and quality thresholds. Local v1 is complete as an experimental engineering artifact. Source/portfolio publication and remote CI verification remain release work; recording a walkthrough is optional.

## Linux CI correction and remaining verification October 7 2026

The first published implementation run failed four Linux lifecycle tests because default piped `ps` output truncated the ownership token after long checkout/artifact paths. Request unlimited command width while retaining the process/token checks. Added a real subprocess regression test with more than 400 argument characters and a guard that local release-version metadata cannot permit project dependency changes. Local checks now pass 121 tests, Ruff and strict mypy, and [both GitHub jobs pass](https://github.com/pushyanthd/recommendation-service/actions/runs/37710120597).

Deferred release publication and retained package version 0.1.0. Built and verified a new non-root/read-only/network-disabled CPU image, audited its dependencies and retained all eight unfixed high scan findings. Rebuilt a real-data bundle from the unchanged frozen treatment. The complete showcase passed all four real recovery drills and 5,000/5,000 HTTP requests with zero failures, 12.07 ms client P95 and 175.5 MiB API RSS. Verified raw accounting and exported [checksummed corrected-code evidence](../evals/ci-corrected-2026-10-07/README.md). The original reports remain intact; the benchmark quality result stays unchanged.

The [engineering verification checklist](release-v1.md) is complete. No release tag or GitHub release has been created. Full publication remains a separate future action at the user’s request.

## v1.0.0 local release preparation — October 7, 2026

Prepared package/lock version 1.0.0 without changing external dependency records, numerical code or the frozen selection. Added distribution targets and CI installation verification: the built wheel is installed non-editably outside the checkout, its source/assets and version are checked, all three fictional methods run offline after explicit dependency setup, and the installed CLI builds/verifies a bundle. The source archive retains the lock/config/reproduction inputs and excludes ignored data/artifacts. Release asset checksums stay outside the source archive to avoid self-referential hashes.

All 121 local tests, Ruff lint/format, strict mypy and the offline fixture validation/freeze/final canary pass. Rebuilt the CPU image and real-data serving snapshot against the release lock. The image passed non-root/read-only/network-disabled HTTP and CPU ALS verification. The dependency audit found no vulnerabilities. The fresh Docker Scout high/critical scan retains eight unfixed high findings with no fixed versions reported. A local OS inventory comparison confirms the same OS package versions as the prior image. The initial automatic scan rejection was resolved by proving the source/build inputs were public and contained no private dataset or secrets; no suppression was used.

The full reference serving protocol completed 200 warmups and 5,000 HTTP requests at 20 requests/second with concurrency capped at four: zero failures, 11.66 ms client P95 and 175.4 MiB API RSS. All four process/file recovery drills passed. Verified raw accounting and exported [checksummed release evidence](../evals/release-v1-2026-10-07/README.md). Quality remains `experimental_quality_objective_failed`, with popularity selected.

No commits, pushes, tags or releases were made, per the user's instruction. [Publishing commands](publishing.md) and [release notes](release-notes-v1.md) are ready. The new distribution step must pass GitHub CI after the user's commit/push; prior jobs cover earlier code/package state. The separate portfolio working tree was left untouched.

## Hardened v1 candidate — October 7, 2026

Switched to digest-pinned Python 3.12.15 on Debian Trixie and staged the required runtime/library closure into a scratch image. Removed shells/package managers, Perl, util-linux and unused terminal/GUI components while retaining Debian control records, license notices and native-library hashes. The image shrank from 344.0 to 244.0 MiB. Verification passes actual healthcheck, non-root/read-only/network-disabled HTTP, library hashes and CPU ALS.

An independent Trivy scan exposed HIGH findings omitted by Scout in the intermediate slim image. Removing their unused runtime packages produced zero Trivy HIGH/CRITICAL, with all lower findings retained. Scout reports one unfixed zlib HIGH. The required C++ library is still affected according to Debian even though current scanners omit it; both advisory risks stay explicit. Complete raw scans, database timestamps, CycloneDX SBOM and clear Python dependency auditing are retained in [new evidence](../evals/hardened-v1-2026-10-07/README.md). No suppression or all-vulnerabilities-fixed claim was used.

Fixed API startup outside the checkout by packaging the unchanged project lock; tests ensure caller locks cannot influence identity. The isolated wheel now passes actual HTTP/page/recommendation checks without a working-directory lock. Local checks pass 137 tests, lint/format and strict mypy. Added a fail-closed CI image gate, full action commit pins and a tag workflow for checksum-listed assets plus provenance/SBOM attestations. Workflow syntax passes locally; new remote CI/attestations await the user's commit/push.

Captured a real fictional-fixture screenshot and captioned walkthrough with desktop/mobile browser assertions. Refit the unchanged frozen MovieLens treatment for the new runtime source. The full protocol completed 5,000 requests with zero failures, 11.65 ms client P95 and 175.8 MiB API RSS; all four process/file recovery drills passed. Raw and aggregate accounting verify. Popularity and the experimental quality label remain unchanged. No commits, tags or releases were made during this work; [publishing](publishing.md) gives the user all commands.
