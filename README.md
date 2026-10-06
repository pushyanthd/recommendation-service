# CPU Recommendation Service

CPU-only movie ranking with chronological splits, full-catalog evaluation, and an offline API demo.

**Status: first development slice.** Popularity, item cosine similarity, and CPU ALS run on a self-authored fictional fixture. The API serves popularity until automatic selection gates are implemented. These fixture results establish functionality, not MovieLens quality or production capacity.

## Run locally

Requires Python 3.12. Installation downloads locked dependencies; tests, the fixture smoke and demo subsequently run offline. No GPU, model API, manual labels or review workflow is needed.

```bash
make setup
make check
make smoke
make demo-fixture
```

Open <http://127.0.0.1:8000>. Choose already-seen fictional movies and get unseen recommendations. The API is also available at `/docs`.

```bash
curl http://127.0.0.1:8000/v1/recommendations \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"k":10}'
```

Only movies observed before the training cutoff enter the prediction catalog. All prior ratings, including low ratings, are excluded from recommendations. Sparse and zero-history profiles have explicit popularity fallback in personalized methods. Unknown IDs are rejected, genre filters are preserved, and an exhausted catalog produces a shorter list.

## Development evidence

`make smoke` trains all three methods on the same fictional pre-cutoff history and scores the validation period. It writes `artifacts/fixture-smoke.json` with per-user metrics, failures, unreachable positives, dataset identity, hardware and training timings. The test period remains reserved. CPU ALS imports `implicit.cpu.als` directly; no accelerator is auto-selected.

The evaluation keeps unreachable positive movies in Recall/NDCG denominators and scores failed recommendations as zero. Hand-computed tests verify metric definitions independently of the ranking models. Timestamp-boundary ties stay in the same period.

## Remaining milestones

- Explicit, checksum-pinned MovieLens ingestion and retained upstream terms.
- Real-data validation comparison, paired intervals and automatic selection gates.
- Verified model bundles, activation/restart/rollback and fault evidence.
- CPU container, telemetry, load/resource benchmark and final frozen reports.

The [architecture plan](arch_plan/recommendation-service-plan.md) defines the complete 12–16 engineer-day scope. This initial slice implements fixture commands only; `data-fetch`, `benchmark`, `dev` and `showcase` are not available yet.

## Documentation

- [Implementation progress](docs/progress.md)
- [Data provenance](docs/data-card.md)
- [Architecture and delivery plan](arch_plan/recommendation-service-plan.md)
