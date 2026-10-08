# v1.0.0 local release verification — October 7, 2026

The v1.0.0 package and selected frozen-treatment MovieLens snapshot passed local engineering verification. No commit, push, tag or GitHub release was made during preparation. The new distribution check still requires CI on the user’s committed revision; prior CI covers the earlier package.

The [standalone showcase](report.html) accounts for 200 warmups and **5,000/5,000 HTTP requests with zero failures**, at 20 offered requests/second and concurrency capped at four. Client P95 was **11.66 ms**, including queueing; peak API-process RSS was **175.4 MiB**. All four real file/process recovery drills passed. Engineering acceptance passed on Apple M1 / 16 GiB. The measurement uses a shared local development host; it is not an exclusive-machine benchmark.

[JSON](report.json), [Markdown](report.md), [container verification](container.json), [security](security.json) and [local checks](local-checks.json) retain results and identities. All 121 tests, Ruff formatting/lint, strict mypy and the offline fixture validation/freeze/final canary pass. A separate non-editable wheel installation outside the source checkout runs all three fictional methods and a CLI bundle roundtrip. Dependency installation explicitly uses a populated cache; these checks do not claim an uncached offline install.

The release image `cpu-reco:v1.0.0` passes CPU/non-root/read-only/network-disabled HTTP verification. Its current high/critical scan records **eight unfixed high findings** with **zero fixed versions reported**. The locked Python dependency audit found zero vulnerabilities. OS package inventories match the previously scanned image. No findings are suppressed or represented as remediated.

The benchmark retains `experimental_quality_objective_failed`: popularity stays selected because personalized methods missed the frozen validation objective. Neither the release version nor the serving check changes the frozen treatment or inspected final quality result.

Raw profile timings, process logs, dataset rows and models remain ignored under `artifacts/full-release-v1`. The exporter verified raw request accounting before producing public aggregates. The manifest covers every public file and binds source, dependency, model, data and image identities. Distribution archive hashes are retained separately with release assets, avoiding a source archive containing its own checksum.

Verification from the prepared local snapshot:

```bash
.venv/bin/reco verify-showcase artifacts/full-release-v1/showcase --root artifacts/full-release-v1/models
.venv/bin/reco verify-showcase evals/release-v1-2026-10-07 --aggregate --root artifacts/full-release-v1/models
```

To show this exact real-data snapshot locally:

```bash
.venv/bin/reco serve --root artifacts/full-release-v1/models
```

A fresh checkout generates its own benchmark/bundle/showcase after explicit setup. See [reproduction](../../docs/reproduction.md), [release readiness](../../docs/release-v1.md) and [commands to commit/publish yourself](../../docs/publishing.md).
