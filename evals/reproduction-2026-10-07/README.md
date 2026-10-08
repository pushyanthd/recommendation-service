# Clean environment reproduction

A new virtual environment installed the project as a non-editable wheel in an isolated copy of the prospective release files. The copy contained no previous environment, prepared dataset, model bundle or local benchmark output. The [summary](summary.json) retains commands, exit codes, package checksums and raw evidence digests.

All 119 tests, Ruff and strict mypy passed. The fictional smoke and validation/final canary passed. Explicit setup rebuilt MovieLens from the pinned original ZIP, then the documented `make benchmark benchmark-final bundle` sequence built a new real-data snapshot. All three methods matched the original numerical treatment identities and every per-user metric exactly, with maximum difference **0.0**. The validation decision remained popularity and the release label remained experimental.

An actual local HTTP process passed readiness, real-data provenance, saved/ephemeral seen-item exclusion and selected-versus-popularity parity checks, then stopped. This is a reproduction check, separate from the original 5,000-request reference load measurement.

Dependency installation used an explicitly supplied populated uv cache with `--locked --offline --no-editable`; it does not establish an empty-cache network installation. The original ZIP was supplied explicitly. Process code and the development dependency lock differ from the October 6 research run, so complete unchanged-treatment execution identity is not claimed. Compatible populations, numerical dependencies, ranking/data/contracts source, model/configuration identities and per-user metrics were checked separately.

The [container verification](container-verification.json) reruns the existing image's CPU, non-root, read-only and network-disabled checks. Its image and package-source identities match the October 7 serving evidence. This rerun does not rescan vulnerabilities; the dated [security findings](../2026-10-07/security.json) remain applicable to that recorded image scan.

Raw logs, reports, prepared data, model files and the runner remain local under ignored `artifacts/reviewer-reproduction-2026-10-07`. The public summary contains no rating rows, user metrics or preference traffic. `checksums.json` covers this guide and the two JSON summaries. Checksums detect file changes and do not authenticate untrusted evidence.
