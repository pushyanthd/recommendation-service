# Data provenance

The packaged fixture contains only self-authored fictional movie titles, genres, user identifiers and rating events. It deliberately includes low ratings, sparse/new users and a movie first observed after training. It is designed to exercise contracts and chronology; its preferences and metrics do not represent a real population.

No MovieLens data rows or trained MovieLens model are included in Git. Explicit setup now downloads the named release, verifies its pinned archive identity, retains the upstream README and terms locally, and records parsed counts/split cutoffs. Real-data assets remain outside Git and distributable images.

## MovieLens 1M setup, October 6, 2026

Source: [GroupLens MovieLens 1M](https://grouplens.org/datasets/movielens/1m/). The downloaded archive's MD5 matches the upstream published checksum, `c4d9eecfca2ab87c1945afe126590906`. Its locally computed SHA-256 is pinned as `a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20`. The [committed manifest](../datasets/manifest.json) records exact source-file/README hashes, counts, encodings, timestamp range and split cutoffs. It contains no rating rows.

Validated counts: 1,000,209 ratings, 6,040 users, 3,883 metadata movies, and 3,706 movies with ratings. Movie titles use Latin-1; ratings use ASCII. All user/movie pairs are unique, ratings are whole stars in 1–5, timestamps are nonnegative, and every rated movie joins to metadata. `users.dat` demographics are not extracted or parsed.

The global split uses strict-before history boundaries at timestamps 975768738 and 978133414: 800,164 training, 100,024 validation and 100,021 final events. All events sharing a boundary timestamp remain together. Four/five-star ratings are positive signals; all prior ratings are seen-item exclusions. Prediction catalogs contain only previously observed movies. Future unreachable positives still count in Recall/NDCG denominators.

The [release README](https://files.grouplens.org/datasets/movielens/ml-1m-README.txt) permits research subject to attribution and conditions. It bars implied endorsement, requires separate permission for redistribution and for commercial or revenue-bearing use, and does not guarantee suitability or accuracy. The complete original terms are retained at `artifacts/datasets/ml-1m/README`. This repository provides fictional fixtures and aggregate benchmark evidence, not a redistributed dataset or a commercial deployment.

Dataset attribution: F. Maxwell Harper and Joseph A. Konstan. 2015. *The MovieLens Datasets: History and Context*. ACM Transactions on Interactive Intelligent Systems 5(4), Article 19. [DOI: 10.1145/2827872](https://doi.org/10.1145/2827872).

MovieLens participation was already filtered by the source. The sparse/zero-history cohorts do not establish performance for arbitrary new real-world users. Missing ratings are unobserved preferences, and timestamps record rating activity rather than verified exposure/viewing times. Offline recovery metrics do not establish engagement, discovery quality, click-through rate or revenue uplift.

The architecture's links to neighboring projects resolve in the original workspace. Those external planning inputs are not dependencies required to install or run this repository.
