# Serving showcase — October 7, 2026

The checksummed [standalone HTML report](report.html) combines the frozen MovieLens comparison with actual HTTP, resource, recovery and container evidence. [JSON](report.json) and [Markdown](report.md) retain the same aggregate result. The exporter verified raw request accounting before export; model histories, dataset rows and raw profile traffic remain local.

The release remains `experimental_quality_objective_failed`. Popularity is selected by validation. Passing engineering/load checks cannot promote item similarity based on its stronger final test result. The [security scan](security.json) retains eight unfixed high image findings; dependency auditing is clear. This is a local benchmark/demo rather than a production-security or online-uplift claim.

The [manifest](manifest.json) binds public files to the active model/data/final-report identities. [Resources](resources.json) separates application measurements, local artifacts, Docker image size and owned hardware. Electricity was not metered. Raw evidence is retained at `artifacts/showcase-2026-10-07`, with the earlier pre-CLI-fix run retained at `artifacts/showcase`.

Verification:

```bash
.venv/bin/reco verify-showcase evals/2026-10-07 --aggregate --root artifacts/models
.venv/bin/reco verify-showcase artifacts/showcase-2026-10-07 --root artifacts/models
```

These active-root checks apply to this exact serving snapshot/code. A fresh reproduction generates its own immutable version/evidence. The [reproduction guide](../../docs/reproduction.md), [rollback runbook](../../docs/rollback.md) and [system card](../../docs/system-card.md) describe setup, operations and limits.
