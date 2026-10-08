# Recommendation service v1.0.0 release readiness

The bounded local v1 is implemented and the v1.0.0 package is prepared locally. No commits, pushes, tags or releases were made during this preparation. Publication remains user-managed; use the [publishing commands](publishing.md) after reviewing the evidence and limits.

## Completed engineering work

- [x] Deliver all nine architecture acceptance criteria: [acceptance mapping](acceptance.md).
- [x] Correct Linux lifecycle ownership checks without weakening them; retain a real long-command subprocess regression test.
- [x] Verify the prior correction on GitHub: [fixture and CPU-image jobs](https://github.com/pushyanthd/recommendation-service/actions/runs/37710650074).
- [x] Assign package version 1.0.0; the lock changes only the local package version and preserves the frozen external dependencies.
- [x] Pass all 121 local tests, Ruff formatting/lint and strict mypy for v1.0.0.
- [x] Add wheel/source archive verification to CI, including an isolated installed-CLI fixture and bundle check.
- [x] Build and verify the v1.0.0 CPU image with non-root/read-only/network-disabled execution.
- [x] Audit the locked Python dependencies: zero vulnerabilities.
- [x] Scan the release image and retain eight unfixed high findings, with zero fixed versions reported.
- [x] Build a v1.0.0 serving snapshot from the unchanged frozen MovieLens treatment.
- [x] Complete 200 warmups, 5,000 HTTP requests and all four process/file recovery drills: zero failures, 11.66 ms client P95 and 175.4 MiB API RSS.
- [x] Verify raw accounting and export checksummed source/bundle/image evidence.
- [x] Build and verify local wheel/source archives with SHA-256 manifests.

The [release evidence](../evals/release-v1-2026-10-07/README.md) records the full serving protocol, recovery checks and package/image identities. Original October 6/7 reports and corrected-code evidence remain immutable historical results.

## User-managed publication

- [ ] Review and commit the prepared release files.
- [ ] Push the commit and verify both GitHub jobs on that exact revision, including the new distribution check.
- [ ] Build/check the final release archives and their SHA-256 manifest.
- [ ] Tag the verified revision `v1.0.0` and publish a GitHub release with the archives and verification receipt.

The commands and draft release notes are in [publishing](publishing.md) and [release notes](release-notes-v1.md). Prior CI cannot verify the new uncommitted distribution step; that check must pass after your push.

## Preserved results and limits

The frozen MovieLens comparison covers 1,188 eligible users with zero scoring failures per method. Item similarity improved final NDCG@10 by 11.97%, but its validation gain was 3.41%, below the frozen 10% objective. Popularity remains selected. The benchmark label `experimental_quality_objective_failed` records that research outcome and remains visible in v1.0.0.

The image scan's eight high findings remain unresolved. This release covers the local benchmark/demo. Authenticated real-user profiles, large-catalog serving, public API deployment and online engagement claims remain outside the architecture's bounded v1 scope. A stronger personalized model would require a separate research protocol and an untouched holdout, rather than tuning on the inspected final test period.
