# CPU Recommendation Service v1.0.0

CPU-only movie recommendations with a typed API, browser demo and an independently reproducible offline evaluation. The release compares popularity, item similarity and ALS; selects the serving method automatically from validation; and carries that decision through hash-verified bundles and process-backed activation/rollback.

- Chronological full-catalog MovieLens 1M comparison for 1,188 final eligible users, with no scoring failures and unreachable positives retained as misses.
- Saved/ephemeral preferences, genre filtering, strict all-seen exclusion, cold-start fallback and an explicit popularity comparison.
- Immutable bundles, atomic selection, readiness verification, restart and rollback recovery, bounded telemetry and CPU Docker packaging.
- 121 passing local tests, lint/types, CPU image verification and isolated installed-wheel fixture checks. CI covers fictional evaluation, package installation and the CPU image.
- Selected-baseline serving completed 5,000 HTTP requests with zero failures, 11.66 ms client P95 and 175.4 MiB API RSS on Apple M1; all four recovery drills passed.
- SHA-256 manifests, standalone HTML/JSON/Markdown evidence, data/system cards and reproduction/demo guides.

Item similarity improved final NDCG@10 by 11.97%, but its validation gain of 3.41% missed the frozen 10% objective. Popularity remains selected and recommendation quality retains its experimental label. The selected baseline is not presented as active personalization. The release image retains eight unfixed high findings; the locked Python dependency audit is clear. Scope is the local benchmark/demo, with no online engagement or production-security claim.

Start with the [README](https://github.com/pushyanthd/recommendation-service/blob/v1.0.0/README.md), [engineering case study](https://github.com/pushyanthd/recommendation-service/blob/v1.0.0/docs/engineering-case-study.md) and [release evidence](https://github.com/pushyanthd/recommendation-service/tree/v1.0.0/evals/release-v1-2026-10-07).

```bash
make setup
make check
make demo-fixture
```

Python 3.12 is required. Dependencies and optional MovieLens setup are explicit network steps. Fixture/runtime execution is offline. Attached wheel/source archives contain fictional fixtures, with no redistributed MovieLens rows or trained real-data bundles. Use the source archive and committed lock for reproducible setup; installing the wheel alone does not pin external dependencies.
