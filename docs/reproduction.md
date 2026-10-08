# Reproducing the CPU comparison

## Offline fixture

Use Python 3.12 and the committed lock. Installation is the dependency-network step; the fixture commands and tests use no network.

```bash
make setup
make check
make smoke
make demo-fixture
```

The browser and API serve the fictional popularity baseline. These are correctness/feasibility results, separate from MovieLens ranking quality.

The [October 7 clean environment check](../evals/reproduction-2026-10-07/README.md) verifies a new non-editable installation, the fixture pipeline, real-data reconstruction and HTTP serving. It explicitly supplies cached dependencies and the pinned local archive; it does not reuse prepared data or trained bundles.

## Explicit real-data setup

```bash
make data-fetch
```

This command downloads only the named MovieLens 1M archive, verifies the pinned SHA-256, validates the ZIP allowlist and byte limits, parses/validates the rating and movie contracts, retains the original README locally, and installs the prepared directory atomically. Demographic records are not extracted. Data rows are ignored by Git. Setup is idempotent only when the installed files and complete manifest still verify; it refuses changed data instead of silently replacing it.

An existing archive supports entirely offline setup:

```bash
.venv/bin/reco data-fetch --archive /path/to/ml-1m.zip
```

## Validation, freeze and final scoring

```bash
make benchmark
make benchmark-final
.venv/bin/reco verify-report artifacts/benchmark/final
```

The first command trains all three methods on the first period, scores the middle period and writes a frozen validation decision. The second command verifies the data, timestamp split, source files, dependency lock, configuration and validation-report digest before refitting the frozen methods on train plus validation and scoring the complete final period. Final metrics never select a new treatment.

The default protocol is [config/benchmark.json](../config/benchmark.json). It uses one ALS configuration, 2,000 paired bootstrap resamples, a 10% relative NDCG@10 objective with a positive lower interval endpoint, and at most 0.01 absolute Recall@20 loss. A near-zero baseline makes the relative gate unusable; it does not automatically pass a candidate. A failed quality gate selects popularity. The benchmark report records research selection before serving gates; the separate [October 7 showcase](../evals/2026-10-07/README.md) records completed HTTP, bundle and lifecycle checks. Preserve both dated results.

Each phase is immutable. To rerun an unchanged treatment or recover from an interrupted run, choose a fresh output directory. Do not change settings based on inspected final labels.

```bash
.venv/bin/reco benchmark --output artifacts/reproduction
.venv/bin/reco benchmark --final --output artifacts/reproduction
.venv/bin/reco verify-report artifacts/reproduction/final \
  --against artifacts/benchmark/final --unchanged-treatment
```

Compatibility checks require matching data, split, catalog, label/metric protocol, cohort/target mapping and completion accounting. An explicitly changed treatment may have different model/configuration identities. `--unchanged-treatment` additionally requires matching code, dependencies and model/configuration identities, with user metric tolerance 1e-6. Missing or incompatible evidence exits nonzero and never rewrites the reference report.

## Evidence files

Each phase contains `report.json` with raw per-user metrics, `report.md`, a standalone `report.html`, and `checksums.json`. The report includes total/eligible/no-target users, failed requests scored as zero, unreachable positives counted as misses, warm/sparse/zero-history cohorts, coverage, popularity concentration, fallback rates, training and in-process scoring times, peak process RSS, library/thread identities and the automatic decisions. These timings do not measure HTTP load.

To export verified aggregate evidence without dataset rows, user identifiers or private library paths:

```bash
.venv/bin/reco export-summary artifacts/benchmark/development evals/local/development
.venv/bin/reco export-summary artifacts/benchmark/final evals/local/final
```

Aggregate exports retain the raw source-report digest and checksummed JSON/Markdown/HTML. They cannot replace raw per-user evidence in compatibility/reproducibility checks. The committed October 6 summaries are a measured research result, not a completed v1 product acceptance report.

Typed data/pipeline failures are saved to `data-failure.json` or the run's `failure.json` and exit nonzero. Process locks reject simultaneous setup or selection in the same artifact root. Benchmarks and report verification have no network-download code path.

## Serving the frozen selection

After explicit data/dependency setup, a fresh checkout can run:

```bash
make benchmark benchmark-final bundle
make dev
```

`make bundle` builds and initially selects the verified snapshot. The default benchmark directory is `artifacts/benchmark`; override `BENCHMARK_DIR` for another immutable run. The original local measured run uses `BENCHMARK_DIR=artifacts/benchmark-2026-10-06`. Bundle construction verifies the complete frozen selection, refits only pre-test history, and retains the final report digest. The API loads one snapshot at startup and performs no runtime downloads, training or preference writes.

If an active pointer already exists, build without `--select`, then activate the new version through the owned process workflow:

```bash
.venv/bin/reco build-bundle --report artifacts/benchmark/final
.venv/bin/reco start
.venv/bin/reco activate --model-id <printed-model-id>
.venv/bin/reco rollback --model-id <previously-verified-model-id>
.venv/bin/reco stop
```

`make dev` runs in the foreground and stops with Ctrl-C. `reco start/stop` manage a detached local process; activation/rollback require that owned process. `reco recover` handles an interrupted pointer change using the last-known-good bundle. Only locally built trusted snapshots are supported. `verify-bundle <directory>` checks a model without training or activation.

The October 7 security update changes only the development pytest dependency. The original benchmark lock is retained under `config/frozen/<original-lock-sha256>.uv.lock`. A verifier permits that documented dev-only change and the local project's release version while requiring every external runtime/other package record and the project's dependency metadata to remain identical, as well as exact installed numerical versions and unchanged ranking/data/contracts source. This does not rewrite the frozen evaluation identity or tune on final labels. The container uses a patched Python 3.12 base; its fictional CPU checks are separate from the original macOS quality measurements.

The Linux lifecycle correction changes serving source identity. The original October 7 reports remain immutable historical evidence; active-root verification of those reports requires their recorded code and bundle. Use a fresh bundle root and showcase output to verify the corrected source, rather than assigning its identity to the old run.

## CPU image and measured showcase

Image construction is an explicit network/setup step. Verification and runtime need no network:

```bash
make image
make image-check
make showcase
.venv/bin/reco verify-showcase artifacts/showcase --root artifacts/models
```

The showcase output is immutable. It runs four recovery drills in isolated processes, performs 200 warmups and 5,000 offered HTTP requests at 20 requests/second with a concurrency cap of four, and produces checksummed JSON/Markdown/HTML plus raw timings. The output remains complete when quality is experimental; incomplete protocol or failed serving objectives exit nonzero. `--output`, `--requests`, `--rate` and `--warmup` support explicitly labeled development checks, which cannot count as the full reference protocol. Repeat into a fresh output directory.

Run the portable fictional container with loopback publication:

```bash
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --cap-drop ALL --security-opt no-new-privileges \
  -p 127.0.0.1:8000:8000 cpu-reco:local
```

For real-data serving, mount the local models directory read-only and match its owner's non-root UID/GID:

```bash
docker run --rm --read-only --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m --cap-drop ALL \
  --security-opt no-new-privileges \
  -v "$PWD/artifacts/models:/opt/models:ro" \
  -p 127.0.0.1:8000:8000 cpu-reco:local
```

`make audit` performs dependency and high/critical image scans; these are explicit network checks. The currently retained unfixed base-image findings make the image audit exit nonzero and remain documented in the system card. Correctness verification is separate from vulnerability status.

Export verified aggregates without distributing models, histories or raw profile traffic:

```bash
.venv/bin/reco export-showcase artifacts/showcase evals/local-showcase
.venv/bin/reco verify-showcase evals/local-showcase --aggregate
```
