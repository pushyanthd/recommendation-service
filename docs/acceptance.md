# Recommendation service v1 acceptance

The bounded local v1 is delivered as an experimental portfolio project. Engineering acceptance passed, including HTTP/resource objectives and all four recovery drills. The personalized quality objective failed validation, so popularity stays active. These are separate outcomes, and the failed objective remains visible.

## Architecture acceptance criteria

The nine criteria in the [architecture plan](../arch_plan/recommendation-service-plan.md#11-test-strategy-and-automated-acceptance) map to the following evidence.

| Criterion | Status | Evidence |
| --- | --- | --- |
| 1. Locked installation, fictional demo and CPU image | Delivered | [Clean environment reproduction](../evals/reproduction-2026-10-07/README.md): new non-editable installation, 119 passing tests, fixture workflow and CPU image recheck; dependency setup explicitly uses a populated cache |
| 2. Explicit validated data setup and offline pipeline | Delivered | [Dataset manifest](../datasets/manifest.json), [data card](data-card.md), archive checksum and immutable split identity |
| 3. Three frozen full-catalog final reports | Delivered | [Final report](../evals/2026-10-06/final/report.html): 1,188 users per method, zero failures, 45 unreachable positives retained |
| 4. Automatic selection and honest release label | Delivered with failed quality objective | [Validation report](../evals/2026-10-06/development/report.html): popularity selected; final label `experimental_quality_objective_failed` |
| 5. Saved and ephemeral browser/API workflow | Delivered | [System card](system-card.md), saved/ephemeral/filter API tests and recorded Chromium verification in [progress](progress.md) |
| 6. Declared hardware and resource measurements | Passed for selected baseline | [Showcase](../evals/2026-10-07/report.html): HTTP P95 11.52 ms, zero failures, API RSS 175.3 MiB; [quality report](../evals/2026-10-06/final/report.html): training-process peak RSS 914 MiB |
| 7. Four failure drills and ranking invariants | Passed | Actual-process [showcase](../evals/2026-10-07/report.html) and [rollback runbook](rollback.md) |
| 8. Checksummed showcase bound to tested identities | Delivered | [Showcase manifest](../evals/2026-10-07/manifest.json), raw and aggregate `verify-showcase` commands in the [evidence guide](../evals/2026-10-07/README.md) |
| 9. Results, limitations, cards and reproduction | Delivered | [README](../README.md), [case study](engineering-case-study.md), [data card](data-card.md), [system card](system-card.md) and [reproduction guide](reproduction.md) |

Engineering completion does not imply that personalization passed or that the service is ready for production. The retained image scan has eight unfixed high findings; `make audit` reports those findings with a nonzero exit. Public hosting, release tags and online experiments are outside local v1 acceptance.

The clean environment reproduction also rebuilt real-data reports and a serving bundle. All three numerical treatment identities matched the original run, and every per-user metric reproduced with maximum difference 0.0. Actual HTTP checks verified readiness, real-data provenance and seen-item exclusion without using the original serving bundle.

## Portfolio release work

The local case study, demo walkthrough and portfolio entry are prepared. The implementation and evidence still need to be committed and published to the source repository, and the updated portfolio needs publication, before remote links expose this release. The configured GitHub Actions workflow must run on that published revision before claiming a remote CI pass. Publishing and tagging are separate actions under the plan.

A screen recording is optional: follow the case study's five minute demo, keep fictional and real-data provenance visible, and show the failed validation gate alongside the final result. Additional recommenders, a learned reranker and cloud infrastructure are follow-up projects rather than requirements for this release.
