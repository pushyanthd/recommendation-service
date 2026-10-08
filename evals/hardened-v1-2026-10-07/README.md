# Hardened v1 candidate — October 7, 2026

The current serving source, frozen-treatment MovieLens snapshot and minimal CPU image passed local engineering verification. No commits, pushes, tags, attestations or release uploads were made during this work. New CI/tag workflows still require the user's commit/push; prior passing CI covers the earlier preparation.

The [standalone HTML showcase](report.html) accounts for 200 warmups and **5,000/5,000 HTTP requests, zero failures**, offered at 20 requests/second with concurrency capped at four. Client P95 is **11.65 ms**, including queueing; API RSS is **175.8 MiB**. All four actual process/file recovery drills passed on the shared Apple M1 / 16 GiB development host. Quality remains `experimental_quality_objective_failed`, with popularity selected. The original numerical treatment and final comparison are unchanged.

[Local checks](local-checks.json) retain 137 passing tests, Ruff lint/format, strict mypy, the fictional validation/freeze/final canary and installed-wheel verification. The isolated wheel now serves real HTTP from a directory without a checkout or working-directory lock. [Browser verification](browser-verification.json) binds the [actual fictional screenshot and captioned recording](../../docs/demo/README.md) to the same runtime source. Desktop/mobile checks pass.

The [container](container.json) records the exact linux/arm64 candidate image, UID, health status and runtime library inventory. Its 244.0 MiB runtime excludes shells/package managers, Perl and unused terminal/session tools. Native-library hashes, read-only/offline configuration, HTTP exclusion and CPU ALS were checked. The package inventory preserves Debian control/source records.

[Security summary](security.json), [complete Trivy scan](trivy.json), [Trivy/database summary](trivy-summary.json), [complete Scout scan](scout.sarif.json), [CycloneDX SBOM](sbom.cdx.json) and [Python dependency audit](dependencies.json) are retained without suppressions. Trivy reports 0 HIGH/CRITICAL, 24 MEDIUM, 10 LOW and 1 UNKNOWN. Scout reports one unfixed zlib HIGH. The required C++ library has an additional tracked Debian advisory despite scanner omission. See [applicability and limits](../../docs/security.md). A passing scanner gate does not imply no known vulnerabilities.

The image ID identifies the tested local candidate; CI separately rebuilds linux/amd64 from the user's eventual tagged commit. New tag-workflow attestations must be verified before publishing its exact artifact bytes. Distribution hashes stay with those release assets, avoiding a source archive that contains its own checksum. The manifest here covers every public evidence file and binds source, lock, bundle, data, final report and image identities. Original dated evidence remains unchanged.

Raw request/accounting/process evidence, datasets and models remain ignored under `artifacts/hardening-v1`. The exporter verified raw accounting before creating these public aggregates.

```bash
.venv/bin/reco verify-showcase artifacts/hardening-v1/showcase --root artifacts/hardening-v1/models
.venv/bin/reco verify-showcase evals/hardened-v1-2026-10-07 --aggregate --root artifacts/hardening-v1/models
.venv/bin/reco serve --root artifacts/hardening-v1/models
```

A fresh checkout reproduces its own reports/bundles after explicit setup. See [reproduction](../../docs/reproduction.md), [release readiness](../../docs/release-v1.md) and [all publishing commands](../../docs/publishing.md).
