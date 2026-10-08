# Benchmark decisions

## October 6, 2026: separate validation freeze from final scoring

Use two explicit offline invocations: `reco benchmark` writes development evidence and its frozen decision; `reco benchmark --final` verifies that identity before reading final labels for scoring. This makes the boundary testable and permits an inspectable development report without accidentally scoring the final period. It replaces the architecture's proposed single-command benchmark interface while preserving its selection/refit/test sequence.

Freeze complete package source/asset checksums, the dependency lock and installed numerical versions, data identity, timestamp cutoffs, protocol and the development report digest. The freeze includes one fixed ALS treatment; the plan's three-configuration limit is an upper bound, not a required parameter sweep. No threshold or treatment was changed after development evidence.

Keep research selection distinct from serving promotion. At this milestone the browser/API served the fictional popularity demo; the October 7 milestone below connects verified real-data bundles and HTTP/resource gates. A quality-passing research candidate still requires serving checks. A negative quality result is reported and popularity remains the conservative selection.

Use stable vectorized score/movie-ID ordering. Stream the model's history fingerprint rather than materializing a million JSON dictionaries. These changes preserve filtering/tie invariants and keep the real-data run below the 2 GiB process-memory objective.

## Evidence and rights boundary

Store source rows, upstream terms and per-user metrics locally under ignored `artifacts/`. Commit only the source/count/split manifest and verified aggregate reports. The aggregate exporter omits user records and private library paths while retaining raw-report digests. Checksums establish file consistency for trusted local evidence; they are not an authentication system for arbitrary external reports.

The benchmark measures recovery of later highly rated movies across the full prediction-time catalog. Rating activity is not exposure or viewing history. Sparse cohorts with fewer than 30 users are descriptive. Future-first-seen movies remain in relevance denominators and count as misses. These decisions remain fixed in the headline metrics.

## October 7, 2026: frozen refit and independent serving evidence

Connect the real-data API to the validation-selected popularity snapshot. Refitting for serialization is permitted only with matching frozen ranking/data/contracts source, installed numerical versions, pre-test history, configuration and catalog identity. Preserve the original final-report digest and quality label; packaging is not an opportunity to promote the stronger test result.

Keep the benchmark implementation fixed and instrument an equivalent serving path. Parity checks cover all three treatments and cold-start/filter behavior. Hash the actual process code/dependency identity and match it against the tested bundle during showcase. Activation effects require process restart and readiness verification; rollback evidence uses actual prior versions and files in an isolated root.

The security audit identified a development-only pytest advisory. Update pytest to the patched range described in the [upstream release](https://github.com/pytest-dev/pytest/releases/tag/9.0.3), preserve the original lock, and accept only that dev-only lock-record difference when reconstructing the frozen numerical treatment. All runtime lock records remain fixed. Use a patched, digest-pinned Python 3.12 container base and an explicit OpenMP runtime so ALS works under Linux. Retain all remaining unfixed image findings and limit claims to the local experimental demo.
