# CPU Recommendation Service v1.0.0

First full software release of the bounded local CPU recommendation service.

## Delivered

- Popularity, item similarity and CPU ALS ranking with chronological full-catalog evaluation.
- Automatic validation-based selection, cold-start fallback and strict exclusion of every previously rated movie.
- Typed FastAPI endpoints and a browser workflow for saved profiles, ephemeral likes, genre filters and popularity comparison.
- Immutable hash-verified model bundles, atomic selection, restart/readiness verification, restoration on activation failure and rollback.
- Structured telemetry, locked dependencies, a non-root CPU image and automated fixture/image CI checks.
- Measured MovieLens results, standalone reports, data/system cards, reproduction instructions and an engineering case study.

## CI correction

Linux process inspection now requests unlimited command width so long checkout/artifact paths cannot hide the ownership token. A real subprocess regression test checks the token survives long arguments. Local release version metadata can change independently of the frozen numerical treatment; dependency records and numerical source identities remain enforced.

## Measured result and limits

The original frozen MovieLens comparison covers 1,188 eligible users with zero scoring failures per method. Item similarity improved final NDCG@10 by 11.97%, but its validation gain was 3.41%, below the frozen 10% objective. Popularity remains selected. The benchmark label `experimental_quality_objective_failed` records that research outcome; it is separate from this full software release.

The October 7 selected-baseline serving measurement completed 5,000 HTTP requests with zero failures and 11.52 ms client P95 on Apple M1 / 16 GiB. The dated image scan documents eight unfixed high findings. This release supports a local benchmark/demo; authenticated real-user profiles, large-catalog serving, public API deployment and online engagement claims are outside its scope.

See the repository README, `docs/engineering-case-study.md`, `docs/acceptance.md`, `docs/reproduction.md` and the checksummed `evals/` reports.
