# CPU recommendation service engineering case study

This project asks whether personalization can improve recovery of future highly rated movies while keeping serving fast and reliable on an ordinary CPU. It compares popularity, item similarity and matrix factorization, then carries the frozen selection through an API, browser demo, immutable model bundles and verified rollback.

The local v1 meets its engineering objectives and remains experimental on recommendation quality. Item similarity improved final NDCG@10 by 11.97%, but its validation gain was only 3.41%, below the frozen 10% objective. Popularity therefore stays selected. The final test characterizes the earlier decision and cannot authorize a new one.

## Architecture and tradeoffs

One offline Python pipeline validates MovieLens 1M, builds global chronological splits, trains three CPU methods and writes comparison reports. FastAPI loads a verified snapshot once at startup. Requests score the entire eligible catalog in memory; a small browser screen compares the selected method with popularity using the same preferences and filters.

At roughly four thousand movies, exact scoring keeps candidate selection reproducible without a separate retrieval service. Training uses NumPy, SciPy and the directly imported CPU ALS implementation. Local immutable files avoid a database or model registry while still providing provenance, atomic selection and rollback. This scope suits a local demonstration; much larger catalogs would require a separate latency and retrieval study.

The implementation separates positive history from all rated movies. Four/five-star ratings train preferences, while every prior rating excludes a movie from recommendations. This prevents a common serving error: recommending an already disliked movie because the training matrix omitted it. Sparse profiles fall back to popularity, and genre filters remain enforced even when fewer than ten items are available.

## Evaluation and model selection

The benchmark trains on the first chronological period, selects on the second, freezes the protocol and treatment, then refits on pre-test history for final scoring. All three variants use the same catalog and eligible users. Movies first observed after the cutoff remain misses in the relevance denominator.

The [final comparison](../evals/2026-10-06/final/report.html) accounts for 1,188 eligible users, 54,452 future positive targets, 45 unreachable targets and zero scoring failures per method. Paired intervals use 2,000 user bootstrap resamples.

| Method | Validation NDCG gain over popularity | Final NDCG@10 | Final Recall@20 |
| --- | ---: | ---: | ---: |
| Popularity | Reference | 0.218277 | 0.093712 |
| Item similarity | +3.41% | 0.244413 | 0.103511 |
| CPU ALS | −2.82% | 0.196194 | 0.108018 |

Item similarity's final absolute NDCG difference is 0.02614, with paired 95% interval [0.01838, 0.03460]. ALS improves Recall@20 while reducing NDCG@10, illustrating why selection needs a declared primary objective. Neither candidate met the validation objective. The [validation report](../evals/2026-10-06/development/report.html) preserves the decision rather than selecting the strongest inspected test result.

## Serving and recovery evidence

The [serving showcase](../evals/2026-10-07/report.html) measures the selected popularity snapshot on Apple M1 / 16 GiB. After 200 warmups, 5,000 HTTP requests at an offered 20 requests/second completed with zero failures. Client P95, including queueing, was 11.52 ms; peak API-process RSS was 175.3 MiB. These results apply to the selected baseline and this request mix. They do not establish full-protocol HTTP latency for the rejected personalized variants.

Four drills use actual processes and files: corrupt candidate rejection, forced gate rejection, restart preserving version/ranking, and rollback restoring the exact prior version. Activation verifies a bundle, replaces the pointer atomically, restarts and probes the requested version. Failed startup restores the prior pointer and process. Arrays load without pickle and undergo mapping, shape, checksum and finiteness checks.

The CPU image passed non-root, read-only and network-disabled checks. The retained October 7 dependency audit found no vulnerabilities; the image scan retains eight unfixed high findings. The [system card](system-card.md) records those findings and the local deployment boundary. MovieLens rating recovery establishes neither engagement nor revenue uplift.

## Five minute demo

1. Run `make demo-fixture` after `make setup`. Open `http://127.0.0.1:8000` and point out the fictional-data badge. For the prepared real-data snapshot, use `make dev` instead.
2. Select a saved profile and compare recommendations. Explain the exclusion of every previously rated title and the retained model/cutoff identity.
3. Choose your own likes, add three titles, apply a genre and compare again. The selected real model is popularity, so the two lists agree. Explain the frozen quality decision rather than presenting this as active personalization.
4. Open the final and validation reports above. Show the stronger final item-similarity result, then the failed validation gate that keeps the baseline selected.
5. Open the serving showcase and show HTTP accounting and all four recovery drills. Use the [rollback runbook](rollback.md) for a live lifecycle demonstration; stop the foreground demo before starting the CLI-owned process.

## Portfolio wording

“Built a CPU-only recommendation API comparing popularity, item similarity and ALS with chronological full-catalog evaluation for 1,188 users; preserved a validation-gated baseline and verified model rollback. Measured 11.52 ms HTTP P95 across 5,000 requests with zero failures on Apple M1.”

The completed scope is summarized in the [acceptance checklist](acceptance.md), with setup and commands in the [reproduction guide](reproduction.md). Future model research needs a new evaluation design and an untouched holdout; the inspected final period cannot become a tuning target.
