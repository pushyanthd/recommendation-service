# Corrected Linux lifecycle verification

The Linux ownership-check correction passes the [GitHub fixture and CPU-image jobs](https://github.com/pushyanthd/recommendation-service/actions/runs/37710120597) and all 121 local tests, Ruff and strict mypy. The package remains at 0.1.0. No release tag or GitHub release has been created.

The [standalone report](report.html) verifies the corrected source with a fresh frozen-treatment MovieLens bundle and a freshly built CPU image. The full protocol completed 5,000/5,000 requests with 0 failures, after 200 warmups at 20 offered requests/second and concurrency capped at four. Client P95 was 12.07 ms, including queueing; peak API-process RSS was 175.5 MiB. All four file/process recovery drills passed. Engineering acceptance passed.

[JSON](report.json), [Markdown](report.md), [security](security.json) and [CI receipts](ci.json) retain aggregate outcomes and identities. The dependency audit found zero vulnerabilities. The final image scan found eight high findings with no fixed versions reported. No findings are suppressed or represented as remediated.

The original frozen MovieLens quality decision is unchanged: popularity remains selected and the benchmark retains `experimental_quality_objective_failed`. The earlier dated reports remain immutable historical evidence.

Raw timings, process logs, model histories and dataset rows remain local under ignored `artifacts/ci-corrected`. The exporter verified raw request accounting before exporting these aggregates. The manifest covers every public file and binds model, code, data and image identities.

Verification from the recorded local snapshot:

```bash
.venv/bin/reco verify-showcase artifacts/ci-corrected/showcase --root artifacts/ci-corrected/models
.venv/bin/reco verify-showcase evals/ci-corrected-2026-10-07 --aggregate --root artifacts/ci-corrected/models
```

A fresh checkout generates its own immutable benchmark, bundle and showcase. See the [reproduction guide](../../docs/reproduction.md) and [readiness checklist](../../docs/release-v1.md).
