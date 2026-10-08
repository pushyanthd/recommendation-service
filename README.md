# CPU Recommendation Service

CPU-only movie ranking with chronological splits, full-catalog evaluation, and an offline API demo.

**Status: end-to-end local benchmark/demo delivered; release remains experimental.** Built a CPU-only recommendation API with chronological full-catalog evaluation, automatic model selection, cold-start fallback and verified rollback. Frozen MovieLens comparisons, real-data serving, the browser workflow, CPU packaging and process-backed showcase evidence are implemented. Neither personalized method passed validation, so popularity remains selected; outstanding unfixed image findings are documented.

For a portfolio review, start with the [engineering case study and demo walkthrough](docs/engineering-case-study.md), then the [v1 acceptance checklist](docs/acceptance.md). The experimental label records a failed personalization objective; engineering acceptance is reported separately.

## Run locally

Requires Python 3.12. Installation downloads locked dependencies; tests, the fixture smoke and demo subsequently run offline. No GPU, model API, manual labels or review workflow is needed.

```bash
make setup
make check
make smoke
make demo-fixture
```

Open <http://127.0.0.1:8000>. Choose a benchmark profile or up to ten liked movies, optionally filter by genre, and compare recommendations with popularity. Fixture and MovieLens modes show explicit provenance. The API is also available at `/docs`.

```bash
curl http://127.0.0.1:8000/v1/recommendations \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"k":10}'
```

Only movies observed before the training cutoff enter the prediction catalog. All prior ratings, including low ratings, are excluded from recommendations. Sparse and zero-history profiles have explicit popularity fallback in personalized methods. Unknown IDs are rejected, genre filters are preserved, and an exhausted catalog produces a shorter list.

## Measured MovieLens result — October 6, 2026

All three frozen methods were refitted on identical pre-test history and scored over the same full prediction-time catalog for **1,188 eligible users**, with **zero scoring failures**. The 54,452 future positives include 45 unreachable targets that remain in the metric denominators.

| Variant | Final NDCG@10 | Final Recall@20 | In-process scoring P95 |
|---|---:|---:|---:|
| Popularity | 0.218277 | 0.093712 | 0.877 ms |
| Item similarity | 0.244413 | 0.103511 | 1.006 ms |
| CPU ALS | 0.196194 | 0.108018 | 0.950 ms |

Item similarity's final NDCG improvement is **11.97%**, with paired absolute difference 0.02614 and 95% interval [0.01838, 0.03460]. However, its validation improvement was **3.41%**, below the frozen 10% objective. Popularity therefore remains selected; the test result cannot retroactively promote item similarity. ALS also missed validation and scored below popularity on final NDCG. No settings or thresholds were changed after development evidence.

Reference hardware is Apple M1 / 16 GiB RAM / arm64 macOS. Final single-method fits took 1.09–2.89 seconds; peak final benchmark process RSS was 914 MiB, below the 2 GiB objective. These scoring timings exclude HTTP; the separately measured serving protocol is below. Full CPU identity and memory observations are retained alongside the reports.

See the standalone [final HTML comparison](evals/2026-10-06/final/report.html), [validation HTML comparison](evals/2026-10-06/development/report.html), and [evidence guide](evals/2026-10-06/README.md). Committed summaries contain verified aggregates, identities and checksums; raw per-user metrics and dataset rows remain local under ignored `artifacts/`.

## Run the real-data benchmark

```bash
make data-fetch                # Explicit pinned dataset setup; retains original terms
make benchmark                 # Validation comparison and frozen decision
make benchmark-final           # Verified frozen refit and final report
.venv/bin/reco verify-report artifacts/benchmark/final
```

All runs after explicit data/dependency setup are offline. The phases are immutable; use a fresh `--output` directory for reproducibility runs. The [reproduction guide](docs/reproduction.md) explains archive reuse, frozen identities, compatible comparisons and aggregate exports. These commands perform no serving promotion.

## Fixture evidence

`make smoke` trains all three methods on the same fictional pre-cutoff history and scores the validation period. It writes `artifacts/fixture-smoke.json` with per-user metrics, failures, unreachable positives, dataset identity, hardware and training timings. The test period remains reserved. CPU ALS imports `implicit.cpu.als` directly; no accelerator is auto-selected.

The evaluation keeps unreachable positive movies in Recall/NDCG denominators and scores failed recommendations as zero. Hand-computed tests verify metric definitions independently of the ranking models. Timestamp-boundary ties stay in the same period.

## Measured serving showcase — October 7, 2026

The selected real-data snapshot passed the reference protocol: **200 warmups, 5,000 HTTP requests at 20 requests/second, concurrency capped at four**, one Uvicorn process, and a fixed saved/ephemeral profile mix. Client latency includes queueing.

| Measurement | Result |
|---|---:|
| Valid requests completed | 5,000 / 5,000 |
| HTTP failures | 0 |
| Client P50 / P95 | 10.56 / 11.52 ms |
| Achieved throughput | 20.00 requests/s |
| Peak API-process RSS | 175.3 MiB |
| Snapshot load / cold readiness wall time | 302.6 / 1831.8 ms |
| Required recovery drills | 4 / 4 passed |

The original 50 ms warm P95 and 2 GiB application-memory objectives passed on Apple M1 / 16 GiB. Inference, training, Docker runtime and whole-system measurements remain distinct. The image passed non-root, read-only, network-disabled HTTP and CPU ALS checks. Chromium verified saved/ephemeral preferences, genre filtering and comparison. **119 tests**, Ruff and strict mypy pass; the offline freeze/final canary was also run locally. CI is configured for these fixture and CPU-image checks; shared runners do not enforce the hardware timing objective.

See the [standalone showcase](evals/2026-10-07/report.html), [evidence guide](evals/2026-10-07/README.md), [system card](docs/system-card.md), and [rollback runbook](docs/rollback.md). Checksummed exports retain raw-run identities and verified accounting. The dependency audit is clear; the image's high/critical scan retains **eight unfixed high findings** and zero fixable high/critical findings. This is a local experimental demo, with no production-security or online-uplift claim.

## Serve and reproduce

After explicit dependency/data setup, a fresh checkout can run:

```bash
make benchmark benchmark-final bundle
make dev
```

`bundle` builds and initially selects the frozen snapshot. Existing selections use CLI activation/rollback instead of silently replacing a pointer. The browser supports saved profiles, ephemeral likes, search, genre filters and an explicit popularity comparison; runtime does not download assets or persist preferences.

```bash
make image                    # Explicit CPU image build/setup
make image-check              # Offline non-root/read-only/no-GPU verification
make showcase                 # Isolated fault/restart/rollback and full HTTP protocol
```

Outputs are immutable; repeat runs need fresh directories. The [reproduction guide](docs/reproduction.md) gives options and commands for the original dated run, verified exports and compatible comparisons. Publishing, tagging, hosting, live collection and online experiments remain separate future work under the [architecture plan](arch_plan/recommendation-service-plan.md).

## Documentation

- [Implementation progress](docs/progress.md)
- [Data provenance](docs/data-card.md)
- [Reproduction](docs/reproduction.md)
- [Benchmark decisions](docs/decisions.md)
- [Architecture and delivery plan](arch_plan/recommendation-service-plan.md)
- [Engineering case study and demo walkthrough](docs/engineering-case-study.md)
- [V1 acceptance checklist](docs/acceptance.md)
- [System card](docs/system-card.md)
- [Activation and rollback](docs/rollback.md)
- [Serving evidence](evals/2026-10-07/README.md)
