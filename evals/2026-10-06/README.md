# Frozen MovieLens CPU comparison — October 6, 2026

This is an experimental offline research result, not a completed service release or HTTP benchmark.

| Evidence | Files |
|---|---|
| Validation selection | [HTML](development/report.html), [JSON](development/report.json), [Markdown](development/report.md), [checksums](development/checksums.json) |
| Frozen final comparison | [HTML](final/report.html), [JSON](final/report.json), [Markdown](final/report.md), [checksums](final/checksums.json) |
| Dataset/count/split identity | [Manifest](../../datasets/manifest.json) |
| Frozen protocol/code/decision | [Freeze](freeze.json) |
| Actual CPU/RAM observations | [Hardware](hardware.json) |
| Artifact bindings | [Evidence manifest](manifest.json) |

The public reports contain aggregate metrics, cohorts, coverage, paired intervals, fit/scoring times, process RSS, dependency/source identities and decisions. Every raw user record and report checksum was verified before export. Dataset rows, demographic records, user identifiers and raw per-user metrics are absent from these exports. Full local evidence remains under `artifacts/benchmark-2026-10-06` and can be checked with `reco verify-report`.

Validation includes 1,103 eligible users. Item similarity improves NDCG@10 by 3.41%, below the 10% objective; ALS misses the objective too. Selection remains popularity. Frozen final scoring includes the same 1,188 eligible users for each method, 54,452 targets and 45 unreachable positives, with zero failures. Item similarity improves final NDCG by 11.97% with a positive paired interval, but test results cannot promote a rejected validation candidate. Final status remains `experimental_quality_objective_failed`.

The default single ALS configuration and all gates remain unchanged. No final-label tuning occurred. Reference hardware is Apple M1 / 16 GiB; RSS measures the application/benchmark process, while latency measures in-process scoring rather than HTTP. No API P95, throughput, rollback, bundle-fault, container or completed product-acceptance claim is supported by this milestone.

[Reproduction commands](../../docs/reproduction.md) install from the lock, explicitly fetch/verify the fixed release, and separate validation freeze from final refit/scoring. Aggregate exports are readable summaries and cannot substitute for raw per-user evidence in reproducibility checks.
