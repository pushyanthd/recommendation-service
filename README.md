# CPU Recommendation Service

CPU-only movie ranking with chronological full-catalog evaluation, a typed API and a browser demo.

**v1.0.0 candidate: locally verified; commit, new-revision CI and publication remain user-managed.** The service compares popularity, item similarity and ALS, preserves validation-based selection, and verifies serving/restart/rollback with actual processes. Personalization missed its frozen validation objective, so popularity remains active and quality retains its experimental label.

For a portfolio review, start with the [engineering case study](docs/engineering-case-study.md), [recorded fixture demo](docs/demo/README.md), [current evidence](evals/hardened-v1-2026-10-07/README.md) and [release checklist](docs/release-v1.md). The [publishing guide](docs/publishing.md) provides all commit, CI, tag, attestation and release commands.

![Actual fictional-fixture browser comparison](docs/demo/fixture-demo.png)

## Run locally

Requires Python 3.12. Setup explicitly downloads locked dependencies; the fixture and runtime subsequently run offline. No GPU, external model API or manually labeled data is required.

```bash
make setup
make check
make smoke
make demo-fixture
```

Open <http://127.0.0.1:8000>. Choose a saved profile or up to ten liked movies, optionally filter by genre, and compare the selected method with popularity. The fixture badge makes its fictional-data scope visible. API documentation is at `/docs`.

```bash
curl http://127.0.0.1:8000/v1/recommendations \
  -H 'Content-Type: application/json' -d '{"user_id":1,"k":10}'
```

All prior ratings, including dislikes, exclude titles from recommendations. Only movies observed before the cutoff enter the prediction catalog. Sparse/zero-history profiles have explicit fallback in personalized methods; invalid IDs are rejected, genre filters are preserved and an exhausted catalog produces a shorter list. Ephemeral preferences are not persisted.

## Frozen MovieLens comparison

All three methods use identical chronological periods, history and full prediction-time catalog. The final report covers **1,188 eligible users**, **zero scoring failures per method**, and 54,452 future positives. The 45 unreachable positives remain misses in metric denominators. User bootstrap intervals use 2,000 resamples.

| Method | Validation NDCG gain | Final NDCG@10 | Final Recall@20 |
| --- | ---: | ---: | ---: |
| Popularity | Reference | 0.218277 | 0.093712 |
| Item similarity | +3.41% | 0.244413 | 0.103511 |
| CPU ALS | −2.82% | 0.196194 | 0.108018 |

Item similarity gained **11.97% final NDCG**, with paired absolute difference 0.02614 and 95% interval [0.01838, 0.03460]. Its validation gain missed the frozen 10% objective. The final test cannot authorize promotion, so popularity remains selected and `experimental_quality_objective_failed` stays visible. Offline rating recovery establishes no viewing, engagement or revenue effect.

See the [final HTML comparison](evals/2026-10-06/final/report.html), [validation report](evals/2026-10-06/development/report.html) and [evaluation evidence](evals/2026-10-06/README.md). On Apple M1 / 16 GiB, final single-method fits took 1.09–2.89 seconds, training-process peak RSS was 914 MiB and in-process scoring P95 was 0.88–1.01 ms. Those timings exclude HTTP.

## Current serving and recovery evidence

The selected real-data snapshot completed **200 warmups and 5,000 HTTP requests at 20 requests/second**, concurrency capped at four, using saved and ephemeral profiles. Client latency includes queueing.

| Measurement | Result |
| --- | ---: |
| Completed / failed | 5,000 / 0 |
| Client P50 / P95 | 10.30 / 11.65 ms |
| Achieved throughput | 20.00 requests/s |
| Peak API-process RSS | 175.8 MiB |
| Snapshot load | 341.3 ms |
| Recovery drills | 4 / 4 passed |

The 50 ms warm P95 and 2 GiB application-memory objectives passed on the shared Apple M1 development host. Drills verify corrupt-candidate rejection, forced gate rejection, restart preserving exact ranking/version and rollback restoring the prior version. Immutable bundles use checksums, strict array/mapping validation, separate positive/all-seen histories and atomic selection. [Current checksummed evidence](evals/hardened-v1-2026-10-07/README.md) binds the source, model, data, image and measured protocol.

**137 local tests**, Ruff lint/format and strict mypy pass. The installed-wheel check runs all three fixture methods, a bundle roundtrip and real HTTP/page startup outside the checkout without a working-directory lock. Actual desktop/mobile browser checks pass; the [screenshot and captioned recording](docs/demo/README.md) contain only fictional titles.

## Packaging and security

The runtime pins official Python by digest and stages the locked environment plus required native libraries into a **244.0 MiB** CPU image. It excludes shells, package managers, Perl and unused terminal/session tools while preserving Debian library owners, versions and hashes. Verification checks UID 10001, a read-only/offline container, real Docker health status, HTTP exclusion and CPU ALS without GPU access.

Trivy reports **zero HIGH/CRITICAL**, with lower-severity findings retained. Independent Scout reports one unfixed zlib HIGH, and the required C++ library has an additional tracked Debian advisory despite scanner omission. The locked Python dependency audit is clear. See the complete [security review](docs/security.md); this local experimental release makes no zero-vulnerability or production-security claim.

```bash
make image image-check audit
make distribution-check
```

CI pins actions to full commits and gates all Trivy HIGH/CRITICAL findings, incomplete inventories, suppressed findings and mismatched image evidence. It retains raw scans and a CycloneDX SBOM. The tag workflow prepares checked Python archives, a linux/amd64 image archive and provenance/SBOM attestations. It does not publish a release automatically. The new workflows still require CI after your commit/push; prior passing GitHub checks cover the earlier source preparation.

The wheel/source/image contain fictional fixtures, with no redistributed MovieLens rows or trained real-data bundles. Source setup uses the committed lock. Plain wheel installation does not pin every external dependency; its packaged lock records provenance and actual installed versions remain part of runtime identity.

## Reproduce the real-data pipeline

```bash
make data-fetch                       # Explicit pinned dataset setup; preserves original terms
make benchmark benchmark-final        # Validation, freeze and final scoring
.venv/bin/reco verify-report artifacts/benchmark/final
make bundle dev                       # Refit the selected frozen treatment and serve it
```

Later runs are offline after explicit setup. The phases and outputs are immutable: use fresh directories for repetition. See [reproduction](docs/reproduction.md), [data terms](docs/data-card.md), [lifecycle/rollback](docs/rollback.md) and [systems protocols](benchmarks/README.md). Real-data evidence remains experimental; a new personalization study needs an untouched holdout.

## Documentation and historical evidence

- [Architecture and delivery plan](arch_plan/recommendation-service-plan.md), [acceptance](docs/acceptance.md) and [progress](docs/progress.md)
- [Engineering case study](docs/engineering-case-study.md), [data card](docs/data-card.md) and [system card](docs/system-card.md)
- [Release readiness](docs/release-v1.md), [release notes](docs/release-notes-v1.md) and [publishing commands](docs/publishing.md)
- Historical [original serving](evals/2026-10-07/README.md), [corrected Linux lifecycle](evals/ci-corrected-2026-10-07/README.md), [clean reproduction](evals/reproduction-2026-10-07/README.md) and [earlier v1 preparation](evals/release-v1-2026-10-07/README.md)
