# Recommendation service release readiness

Finish and verify the remaining project work before publishing a full release. No release tag or GitHub release has been published. Package version 0.1.0 remains in use during this work.

## Remaining work

- [x] Correct the Linux CI lifecycle failure without weakening process ownership checks.
- [x] Add a real subprocess regression test for long arguments and verify local checks.
- [x] Verify both GitHub fixture and CPU-image jobs on the correction: [passing run](https://github.com/pushyanthd/recommendation-service/actions/runs/37709752278).
- [ ] Build and verify the final CPU image against the corrected source and current package metadata.
- [ ] Audit dependencies and scan that final image; retain its actual findings and applicable fixes.
- [ ] Rebuild a serving snapshot from the unchanged frozen MovieLens treatment.
- [ ] Run the complete 200-warmup/5,000-request HTTP protocol and all four recovery drills for that snapshot.
- [ ] Verify and export checksummed evidence bound to the final source, bundle and image identities.
- [ ] Reconcile the README, acceptance mapping and progress with the final verified state.
- [ ] Confirm GitHub CI passes on the final project revision.

Only after those tasks are complete should the full software release version, tag and GitHub release be published. Release publication remains a separate step.

## Preserved results and limits

The frozen MovieLens comparison covers 1,188 eligible users with zero scoring failures per method. Item similarity improved final NDCG@10 by 11.97%, but its validation gain was 3.41%, below the frozen 10% objective. Popularity remains selected. The benchmark label `experimental_quality_objective_failed` records that research outcome and cannot be removed by renaming the software release.

The original October 7 baseline serving measurement completed 5,000 HTTP requests with zero failures and 11.52 ms client P95 on Apple M1 / 16 GiB. Its image scan documents eight unfixed high findings. These dated reports remain historical evidence; they do not substitute for checking the corrected process code.

The planned full release covers the local benchmark/demo. Authenticated real-user profiles, large-catalog serving, public API deployment and online engagement claims remain outside the architecture's bounded v1 scope.
